import socket
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.constants import FLAG_ACK, FLAG_DATA, FLAG_FIN
from shared.packet_struct import pack_packet
from shared.rdt_core import reliable_recv, reliable_send


LOOPBACK = "127.0.0.1"


def make_udp_socket() -> socket.socket:
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((LOOPBACK, 0))
    return udp_socket


class RDTPeerFilteringTests(unittest.TestCase):
    def test_receiver_ignores_data_and_fin_from_unexpected_peer(self) -> None:
        receiver = make_udp_socket()
        expected_sender = make_udp_socket()
        attacker = make_udp_socket()
        self.addCleanup(receiver.close)
        self.addCleanup(expected_sender.close)
        self.addCleanup(attacker.close)

        payload = b"payload-from-expected-peer" * 80
        result: dict[str, object] = {}

        def receive() -> None:
            try:
                result["data"] = reliable_recv(
                    receiver,
                    expected_peer=expected_sender.getsockname(),
                )
            except BaseException as exc:
                result["error"] = exc

        receive_thread = threading.Thread(target=receive)
        receive_thread.start()

        receiver_address = receiver.getsockname()
        attacker.sendto(
            pack_packet(seq=0, ack=0, flags=FLAG_DATA, data=b"attacker"),
            receiver_address,
        )
        attacker.sendto(
            pack_packet(seq=1, ack=0, flags=FLAG_FIN),
            receiver_address,
        )
        time.sleep(0.05)

        reliable_send(expected_sender, receiver_address, payload)
        receive_thread.join(5.0)

        self.assertFalse(receive_thread.is_alive(), "Receiver did not finish")
        self.assertNotIn("error", result)
        self.assertEqual(result.get("data"), payload)

    def test_sender_ignores_ack_and_fin_from_unexpected_peer(self) -> None:
        sender = make_udp_socket()
        receiver = make_udp_socket()
        attacker = make_udp_socket()
        self.addCleanup(sender.close)
        self.addCleanup(receiver.close)
        self.addCleanup(attacker.close)

        payload = b"sender-peer-filter" * 200
        result: dict[str, object] = {}

        def send() -> None:
            try:
                reliable_send(sender, receiver.getsockname(), payload)
            except BaseException as exc:
                result["send_error"] = exc

        def receive() -> None:
            try:
                result["data"] = reliable_recv(
                    receiver,
                    expected_peer=sender.getsockname(),
                )
            except BaseException as exc:
                result["receive_error"] = exc

        send_thread = threading.Thread(target=send)
        send_thread.start()

        sender_address = sender.getsockname()
        forged_ack = pack_packet(seq=0, ack=9999, flags=FLAG_ACK)
        forged_fin = pack_packet(seq=9999, ack=0, flags=FLAG_FIN)
        for _ in range(5):
            attacker.sendto(forged_ack, sender_address)
            attacker.sendto(forged_fin, sender_address)

        receive_thread = threading.Thread(target=receive)
        receive_thread.start()
        send_thread.join(5.0)
        receive_thread.join(5.0)

        self.assertFalse(send_thread.is_alive(), "Sender did not finish")
        self.assertFalse(receive_thread.is_alive(), "Receiver did not finish")
        self.assertNotIn("send_error", result)
        self.assertNotIn("receive_error", result)
        self.assertEqual(result.get("data"), payload)


if __name__ == "__main__":
    unittest.main()
