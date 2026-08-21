import hashlib
import re
import socket
import tempfile
import unittest
from collections import deque
from pathlib import Path
from unittest.mock import patch

from client.control.context import ClientContext
from client.control.handlers.transfer_handler import handle_appe, handle_stou
from server.control.handlers.transfer_handler import (
    handle_appe as handle_server_appe,
    handle_stou as handle_server_stou,
)
from server.control.session import ClientSession
from tests.reporting import VietnameseTestCase


class FakeControlConnection:
    def __init__(self, replies: list[str]) -> None:
        self.commands: list[str] = []
        self.read_count = 0
        self.replies = deque(replies)

    def send_command(self, command: str) -> None:
        self.commands.append(command)

    def read_reply_line(self) -> str:
        self.read_count += 1
        return self.replies.popleft()


class AppeStouClientTests(VietnameseTestCase):
    suite_title = "APPE VÀ STOU PHÍA CLIENT"

    def _make_upload_context(self) -> ClientContext:
        context = ClientContext(server_host="127.0.0.1")
        context.data_connection_mode = "PASSIVE"
        context.data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        context.data_peer_address = ("127.0.0.1", 9999)
        return context

    def test_appe_does_not_hash_the_complete_remote_file(self) -> None:
        """APPE không tự HASH vì local chỉ chứa phần dữ liệu nối thêm"""
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_path = Path(temp_dir) / "append.bin"
            upload_path.write_bytes(b"new-data")
            context = self._make_upload_context()
            control = FakeControlConnection([
                "150 Ready to append data to append.bin.",
                "226 Data appended to append.bin successfully. "
                "APPENDED_BYTES=8 FINAL_SIZE=20",
            ])

            with (
                patch(
                    "client.control.handlers.transfer_handler._resolve_local_upload_path",
                    return_value=upload_path,
                ),
                patch(
                    "client.control.handlers.transfer_handler._resolve_upload_peer",
                    return_value=("127.0.0.1", 9999),
                ),
                patch("client.control.handlers.transfer_handler.reliable_send"),
            ):
                self.assertTrue(handle_appe(control, context, "append.bin"))
                transfer_thread = context.transfer_thread
                if transfer_thread is not None:
                    transfer_thread.join(2.0)

            self.assertFalse(context.transfer_in_progress)
            self.assertEqual(control.commands, ["APPE append.bin"])
            self.assertEqual(control.read_count, 2)
            self.assertEqual(len(control.replies), 0)

    def test_stou_hashes_the_server_generated_name(self) -> None:
        """STOU đọc REMOTE_NAME và HASH đúng tên do server sinh ra"""
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = b"payload"
            upload_path = Path(temp_dir) / "local.bin"
            upload_path.write_bytes(payload)
            remote_name = "file_0123456789abcdef0123456789abcdef.dat"
            expected_hash = hashlib.sha256(payload).hexdigest()
            context = self._make_upload_context()
            control = FakeControlConnection([
                f"150 Ready to receive a uniquely named file. REMOTE_NAME={remote_name}",
                f"226 File stored successfully. REMOTE_NAME={remote_name} BYTES=7",
                f"200 SHA-256 {remote_name} {expected_hash}",
            ])

            with (
                patch(
                    "client.control.handlers.transfer_handler._resolve_local_upload_path",
                    return_value=upload_path,
                ),
                patch(
                    "client.control.handlers.transfer_handler._resolve_upload_peer",
                    return_value=("127.0.0.1", 9999),
                ),
                patch("client.control.handlers.transfer_handler.reliable_send"),
            ):
                self.assertTrue(handle_stou(control, context, "local.bin"))
                transfer_thread = context.transfer_thread
                if transfer_thread is not None:
                    transfer_thread.join(2.0)

            self.assertFalse(context.transfer_in_progress)
            self.assertEqual(control.commands, ["STOU", f"HASH {remote_name}"])
            self.assertNotIn("HASH local.bin", control.commands)
            self.assertEqual(control.read_count, 3)
            self.assertEqual(len(control.replies), 0)


class AppeStouServerTests(VietnameseTestCase):
    suite_title = "APPE VÀ STOU PHÍA SERVER"

    @staticmethod
    def _make_active_session(server_root: Path) -> ClientSession:
        session = ClientSession(
            client_address=("127.0.0.1", 2121),
            server_root=server_root,
        )
        session.data_connection_mode = "ACTIVE"
        session.active_udp_address = ("127.0.0.1", 9999)
        return session

    def test_stou_uses_collision_resistant_names_and_reports_them(self) -> None:
        """STOU sinh tên UUID khác nhau và trả REMOTE_NAME cho client"""
        with tempfile.TemporaryDirectory() as temp_dir:
            server_root = Path(temp_dir)
            names: list[str] = []

            for _ in range(2):
                replies = handle_server_stou(
                    self._make_active_session(server_root)
                )
                preliminary_reply = next(replies).format()
                replies.close()
                match = re.search(r"REMOTE_NAME=([^\s]+)", preliminary_reply)
                self.assertIsNotNone(match)
                names.append(match.group(1))

            self.assertNotEqual(names[0], names[1])
            for name in names:
                self.assertRegex(name, r"^file_[0-9a-f]{32}\.dat$")

    def test_appe_reports_appended_bytes_and_final_size(self) -> None:
        """APPE trả số byte nối thêm và kích thước cuối của file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            server_root = Path(temp_dir)
            destination = server_root / "existing.bin"
            destination.write_bytes(b"old")
            control_server, control_client = socket.socketpair()
            self.addCleanup(control_server.close)
            self.addCleanup(control_client.close)
            session = self._make_active_session(server_root)
            session.control_conn = control_server

            def receive_append(session, file_path, *, append=False) -> int:
                self.assertTrue(append)
                with file_path.open("ab") as output_file:
                    output_file.write(b"new")
                return 3

            with patch(
                "server.control.handlers.transfer_handler.receive_file",
                side_effect=receive_append,
            ):
                replies = handle_server_appe(session, "existing.bin")
                preliminary_reply = next(replies).format()
                self.assertTrue(preliminary_reply.startswith("150 "))
                with self.assertRaises(StopIteration):
                    next(replies)

                control_client.settimeout(2.0)
                final_reply = control_client.recv(1024).decode("utf-8")

            self.assertIn("APPENDED_BYTES=3", final_reply)
            self.assertIn("FINAL_SIZE=6", final_reply)
            self.assertEqual(destination.read_bytes(), b"oldnew")


if __name__ == "__main__":
    unittest.main()
