import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client.control.context import ClientContext
from client.control.handlers.transfer_handler import _wait_for_active_upload_peer
from server.control.data_transfer_service import receive_file
from server.control.session import ClientSession
from shared.rdt_core import reliable_send


LOOPBACK = "127.0.0.1"


class ActiveUploadTests(unittest.TestCase):
    def test_active_upload_handshake_and_transfer(self) -> None:
        payload = (b"active-upload-integration\x00" * 200) + b"done"

        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "uploaded.bin"
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_socket.bind((LOOPBACK, 0))
            self.addCleanup(client_socket.close)

            server_session = ClientSession(
                client_address=(LOOPBACK, 2121),
                server_root=Path(temp_dir),
            )
            server_session.data_connection_mode = "ACTIVE"
            server_session.active_udp_address = client_socket.getsockname()
            result: dict[str, object] = {}

            def receive_on_server() -> None:
                try:
                    result["size"] = receive_file(server_session, destination)
                except BaseException as exc:
                    result["error"] = exc

            server_thread = threading.Thread(target=receive_on_server)
            server_thread.start()

            client_context = ClientContext(server_host=LOOPBACK)
            client_context.data_connection_mode = "ACTIVE"
            server_peer = _wait_for_active_upload_peer(
                client_socket,
                client_context,
            )
            reliable_send(client_socket, server_peer, payload)

            server_thread.join(5.0)
            self.assertFalse(server_thread.is_alive(), "Active upload did not finish")
            self.assertNotIn("error", result)
            self.assertEqual(result.get("size"), len(payload))
            self.assertEqual(destination.read_bytes(), payload)
            self.assertIsNone(server_session.current_data_socket)


if __name__ == "__main__":
    unittest.main()
