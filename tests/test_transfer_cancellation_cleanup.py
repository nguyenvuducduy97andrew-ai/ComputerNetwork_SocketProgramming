import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.control.data_transfer_service import receive_file
from server.control.session import ClientSession
from shared.rdt_core import reliable_recv, reliable_send


LOOPBACK = "127.0.0.1"


class RDTCancellationTests(unittest.TestCase):
    def test_reliable_send_raises_interrupted_error_when_cancelled(self) -> None:
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        unused_receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        unused_receiver.bind((LOOPBACK, 0))
        self.addCleanup(sender.close)
        self.addCleanup(unused_receiver.close)
        cancel_event = threading.Event()
        result: dict[str, object] = {}

        def send() -> None:
            try:
                reliable_send(
                    sender,
                    unused_receiver.getsockname(),
                    b"cancel-send" * 200,
                    cancel_event=cancel_event,
                )
            except BaseException as exc:
                result["error"] = exc

        send_thread = threading.Thread(target=send)
        send_thread.start()
        time.sleep(0.05)
        cancel_event.set()
        send_thread.join(5.0)

        self.assertFalse(send_thread.is_alive(), "Cancelled sender did not stop")
        self.assertIsInstance(result.get("error"), InterruptedError)

    def test_reliable_recv_raises_interrupted_error_when_cancelled(self) -> None:
        receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver.bind((LOOPBACK, 0))
        self.addCleanup(receiver.close)
        cancel_event = threading.Event()
        result: dict[str, object] = {}

        def receive() -> None:
            try:
                reliable_recv(receiver, cancel_event=cancel_event)
            except BaseException as exc:
                result["error"] = exc

        receive_thread = threading.Thread(target=receive)
        receive_thread.start()
        time.sleep(0.05)
        cancel_event.set()
        receive_thread.join(5.0)

        self.assertFalse(receive_thread.is_alive(), "Cancelled receiver did not stop")
        self.assertIsInstance(result.get("error"), InterruptedError)


class SessionCleanupTests(unittest.TestCase):
    def test_cleanup_cancels_worker_closes_sockets_and_suppresses_reply(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            passive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            passive_socket.bind((LOOPBACK, 0))
            control_server, control_client = socket.socketpair()
            self.addCleanup(control_client.close)

            session = ClientSession(
                client_address=(LOOPBACK, 2121),
                server_root=Path(temp_dir),
            )
            session.control_conn = control_server
            session.data_connection_mode = "PASSIVE"
            session.passive_udp_socket = passive_socket
            destination = Path(temp_dir) / "partial.bin"
            session.start_transfer("STOR", destination, direction="UPLOAD")

            def worker() -> str:
                receive_file(session, destination)
                return "226 transfer should not complete\r\n"

            session.run_transfer(worker)

            deadline = time.monotonic() + 1.0
            while session.current_data_socket is None and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertIs(session.current_data_socket, passive_socket)

            session.cleanup(wait_timeout=3.0)
            session.cleanup(wait_timeout=3.0)

            worker_thread = session.transfer_thread
            self.assertTrue(worker_thread is None or not worker_thread.is_alive())
            self.assertTrue(session.cleanup_started)
            self.assertTrue(session.suppress_transfer_reply)
            self.assertIsNone(session.control_conn)
            self.assertIsNone(session.current_data_socket)
            self.assertIsNone(session.passive_udp_socket)
            self.assertIsNone(session.data_connection_mode)
            self.assertFalse(session.transfer_in_progress)
            self.assertFalse(destination.exists())

            control_client.settimeout(0.1)
            with self.assertRaises(socket.timeout):
                control_client.recv(1024)
            control_server.close()


if __name__ == "__main__":
    unittest.main()
