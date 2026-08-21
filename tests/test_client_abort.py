import socket
import tempfile
import threading
import unittest
from collections import deque
from pathlib import Path
from unittest.mock import patch

from client.control.context import ClientContext
from client.control.handlers.transfer_handler import handle_abor, handle_stor
from tests.reporting import VietnameseTestCase


class FakeControlConnection:
    def __init__(self, replies: list[str] | None = None) -> None:
        self.commands: list[str] = []
        self.read_count = 0
        self.replies = deque(replies or ["200 No transfer in progress to abort."])

    def send_command(self, command: str) -> None:
        self.commands.append(command)

    def read_reply_line(self) -> str:
        self.read_count += 1
        return self.replies.popleft()


class ClientAbortTests(VietnameseTestCase):
    suite_title = "LỆNH ABOR PHÍA CLIENT"

    def test_active_transfer_abor_is_sent_without_competing_for_reply(self) -> None:
        """Client gửi ABOR và để worker hiện tại giữ quyền đọc reply"""
        context = ClientContext(server_host="127.0.0.1")
        control = FakeControlConnection()
        cancel_seen = threading.Event()
        release_worker = threading.Event()

        def worker() -> None:
            context.transfer_cancel_event.wait(2.0)
            cancel_seen.set()
            release_worker.wait(2.0)

        context.start_transfer(worker)
        self.assertTrue(handle_abor(control, context))
        self.assertTrue(cancel_seen.wait(1.0))
        self.assertEqual(control.commands, ["ABOR"])
        self.assertEqual(control.read_count, 0)

        release_worker.set()
        transfer_thread = context.transfer_thread
        if transfer_thread is not None:
            transfer_thread.join(2.0)
        self.assertFalse(context.transfer_in_progress)

    def test_stor_can_be_aborted_without_leaving_a_stale_reply(self) -> None:
        """STOR nền nhận đúng reply ABOR và không để reply thừa"""
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_path = Path(temp_dir) / "upload.bin"
            upload_path.write_bytes(b"payload")
            data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            context = ClientContext(server_host="127.0.0.1")
            context.data_connection_mode = "PASSIVE"
            context.data_socket = data_socket
            context.data_peer_address = ("127.0.0.1", 9999)
            control = FakeControlConnection([
                "150 Ready to receive upload.bin.",
                "226 Abort command successful.",
            ])

            def wait_until_cancelled(*args, **kwargs) -> None:
                cancel_event = kwargs["cancel_event"]
                cancel_event.wait(2.0)
                raise InterruptedError("Transfer aborted.")

            with (
                patch(
                    "client.control.handlers.transfer_handler._resolve_local_upload_path",
                    return_value=upload_path,
                ),
                patch(
                    "client.control.handlers.transfer_handler._resolve_upload_peer",
                    return_value=("127.0.0.1", 9999),
                ),
                patch(
                    "client.control.handlers.transfer_handler.reliable_send",
                    side_effect=wait_until_cancelled,
                ),
            ):
                self.assertTrue(handle_stor(control, context, "upload.bin"))
                self.assertTrue(handle_abor(control, context))
                transfer_thread = context.transfer_thread
                if transfer_thread is not None:
                    transfer_thread.join(2.0)

            self.assertFalse(context.transfer_in_progress)
            self.assertEqual(control.commands, ["STOR upload.bin", "ABOR"])
            self.assertEqual(control.read_count, 2)
            self.assertEqual(len(control.replies), 0)


if __name__ == "__main__":
    unittest.main()
