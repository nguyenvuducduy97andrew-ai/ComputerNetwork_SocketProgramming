import unittest
from unittest.mock import patch

from client.control.handlers.transfer_handler import (
    _send_upload_and_wait_for_completion,
)
from shared.rdt_core import RDTTeardownTimeout


class FakeControlConnection:
    def __init__(self, reply: str):
        self.reply = reply
        self.read_count = 0

    def read_reply_line(self) -> str:
        self.read_count += 1
        return self.reply


class UploadCompletionTests(unittest.TestCase):
    def test_tcp_226_confirms_upload_after_udp_teardown_timeout(self) -> None:
        control = FakeControlConnection("226 Transfer complete")

        with patch(
            "client.control.handlers.transfer_handler.reliable_send",
            side_effect=RDTTeardownTimeout("FIN-ACK lost"),
        ):
            completed = _send_upload_and_wait_for_completion(
                control, object(), ("127.0.0.1", 9999), b"payload"
            )

        self.assertTrue(completed)
        self.assertEqual(control.read_count, 1)

    def test_tcp_failure_rejects_upload_after_udp_teardown_timeout(self) -> None:
        control = FakeControlConnection("426 Transfer aborted")

        with patch(
            "client.control.handlers.transfer_handler.reliable_send",
            side_effect=RDTTeardownTimeout("FIN-ACK lost"),
        ):
            completed = _send_upload_and_wait_for_completion(
                control, object(), ("127.0.0.1", 9999), b"payload"
            )

        self.assertFalse(completed)
        self.assertEqual(control.read_count, 1)


if __name__ == "__main__":
    unittest.main()
