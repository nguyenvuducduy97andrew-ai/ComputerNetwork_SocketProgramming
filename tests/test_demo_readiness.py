import os
import socket
import stat
import tempfile
import unittest
from collections import deque
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from client.control.context import ClientContext
from client.control.data_transfer_service import (
    prepare_upload_data,
    process_download_data,
)
from client.control.handlers.transfer_handler import handle_stor
from server.control.handlers.common_handler import handle_help
from server.control.handlers.navigation_handler import (
    _remove_empty_directory,
    handle_mdtm,
    handle_rmd,
    handle_stat,
)
from server.control.session import ClientSession
from server.control.transfer_codec import decode_from_transfer, encode_for_transfer
from server.main_server import DEFAULT_SERVER_ROOT
from shared.block_mode import BlockModeError, decode_blocks, encode_blocks
from shared.constants import FLAG_DATA
from shared.packet_struct import pack_packet, unpack_packet
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


class BlockModeTests(VietnameseTestCase):
    suite_title = "MODE B"

    def test_block_mode_round_trip_handles_empty_and_multiple_blocks(self) -> None:
        """MODE B đóng khung và giải mã đúng cả file rỗng lẫn nhiều block"""
        for payload in (b"", b"hello", os.urandom(70_000)):
            framed = encode_blocks(payload)
            self.assertEqual(decode_blocks(framed), payload)

    def test_client_and_server_share_the_same_block_framing(self) -> None:
        """Client và server tương thích hai chiều khi dùng MODE B"""
        payload = b"block-mode" * 10_000

        server_wire = encode_for_transfer(payload, "I", "B")
        self.assertEqual(process_download_data(server_wire, "I", "B"), payload)

        with tempfile.TemporaryDirectory() as temp_dir:
            upload_path = Path(temp_dir) / "upload.bin"
            upload_path.write_bytes(payload)
            client_wire = prepare_upload_data(upload_path, "I", "B")

        self.assertEqual(decode_from_transfer(client_wire, "I", "B"), payload)

    def test_block_mode_rejects_payload_without_eof(self) -> None:
        """MODE B từ chối framing thiếu block EOF"""
        with self.assertRaises(BlockModeError):
            decode_blocks(b"\x00\x00\x01x")

    def test_packet_parser_rejects_a_mismatched_payload_length(self) -> None:
        """Packet parser từ chối header khai báo sai độ dài payload"""
        packet = bytearray(pack_packet(seq=1, ack=0, flags=FLAG_DATA, data=b"x"))
        packet[10:12] = (2).to_bytes(2, "big")

        with self.assertRaises(ValueError):
            unpack_packet(bytes(packet))


class CommandConsistencyTests(VietnameseTestCase):
    suite_title = "TÍNH NHẤT QUÁN COMMAND"

    def test_default_server_root_is_separate_from_client_downloads(self) -> None:
        """Server mặc định dùng data/server_storage riêng biệt"""
        self.assertEqual(DEFAULT_SERVER_ROOT, Path("data") / "server_storage")

    def test_help_stou_matches_the_client_cli(self) -> None:
        """HELP STOU yêu cầu tên file local giống client CLI"""
        with tempfile.TemporaryDirectory() as temp_dir:
            session = ClientSession(
                client_address=("127.0.0.1", 2121),
                server_root=Path(temp_dir),
            )
            reply = handle_help(session, "STOU")

        self.assertIn("Syntax: STOU <local-file>", reply)

    def test_stat_supports_file_metadata(self) -> None:
        """STAT nhận file và trả metadata thay vì báo sai kiểu path"""
        with tempfile.TemporaryDirectory() as temp_dir:
            server_root = Path(temp_dir)
            target = server_root / "sample.txt"
            target.write_bytes(b"data")
            session = ClientSession(
                client_address=("127.0.0.1", 2121),
                server_root=server_root,
            )

            reply = handle_stat(session, "sample.txt")

        self.assertTrue(reply.startswith("200 "))
        self.assertIn("sample.txt", reply)
        self.assertIn("4", reply)

    def test_mdtm_uses_compact_utc_format(self) -> None:
        """MDTM trả UTC theo định dạng YYYYMMDDhhmmss"""
        with tempfile.TemporaryDirectory() as temp_dir:
            server_root = Path(temp_dir)
            target = server_root / "sample.txt"
            target.write_bytes(b"data")
            timestamp = 1_704_164_645  # 2024-01-02 03:04:05 UTC
            os.utime(target, (timestamp, timestamp))
            session = ClientSession(
                client_address=("127.0.0.1", 2121),
                server_root=server_root,
            )

            reply = handle_mdtm(session, "sample.txt")

        self.assertEqual(reply, "213 20240102030405\r\n")

    def test_rmd_removes_an_empty_directory(self) -> None:
        """RMD xóa được thư mục rỗng"""
        with tempfile.TemporaryDirectory() as temp_dir:
            server_root = Path(temp_dir)
            target = server_root / "empty"
            target.mkdir()
            session = ClientSession(
                client_address=("127.0.0.1", 2121),
                server_root=server_root,
            )

            reply = handle_rmd(session, "empty")

            self.assertEqual(reply, "250 Removed directory empty\r\n")
            self.assertFalse(target.exists())

    def test_rmd_keeps_a_non_empty_directory(self) -> None:
        """RMD từ chối thư mục có dữ liệu và không xóa nhầm nội dung"""
        with tempfile.TemporaryDirectory() as temp_dir:
            server_root = Path(temp_dir)
            target = server_root / "non-empty"
            target.mkdir()
            (target / "keep.txt").write_text("keep", encoding="utf-8")
            session = ClientSession(
                client_address=("127.0.0.1", 2121),
                server_root=server_root,
            )

            reply = handle_rmd(session, "non-empty")

            self.assertEqual(reply, "550 Directory is not empty.\r\n")
            self.assertTrue((target / "keep.txt").is_file())

    def test_rmd_retries_a_read_only_onedrive_directory_on_windows(self) -> None:
        """RMD bỏ cờ read-only và thử lại cho thư mục OneDrive trên Windows"""
        target = MagicMock(spec=Path)
        target.rmdir.side_effect = [PermissionError(13, "Access denied"), None]
        target.stat.return_value.st_mode = stat.S_IREAD

        with patch("server.control.handlers.navigation_handler.os.name", "nt"):
            _remove_empty_directory(target)

        self.assertEqual(target.rmdir.call_count, 2)
        target.chmod.assert_called_once_with(stat.S_IREAD | stat.S_IWRITE)

    def test_type_a_upload_skips_byte_hash_verification(self) -> None:
        """TYPE A không báo hash mismatch giả do chuyển đổi newline"""
        with tempfile.TemporaryDirectory() as temp_dir:
            upload_path = Path(temp_dir) / "text.txt"
            upload_path.write_bytes(b"first\nsecond\n")
            context = ClientContext(server_host="127.0.0.1")
            context.transfer_type = "A"
            context.data_connection_mode = "PASSIVE"
            context.data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            context.data_peer_address = ("127.0.0.1", 9999)
            control = FakeControlConnection([
                "150 Ready to receive text.txt.",
                "226 File text.txt received successfully. 15 bytes stored.",
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
                redirect_stdout(StringIO()) as output,
            ):
                self.assertTrue(handle_stor(control, context, "text.txt"))
                transfer_thread = context.transfer_thread
                if transfer_thread is not None:
                    transfer_thread.join(2.0)

            self.assertEqual(control.commands, ["STOR text.txt"])
            self.assertEqual(control.read_count, 2)
            self.assertIn("skipped for TYPE A", output.getvalue())


if __name__ == "__main__":
    unittest.main()
