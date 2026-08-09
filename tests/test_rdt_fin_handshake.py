import socket
import threading
import unittest
from unittest.mock import patch

from shared.checksum import verify_checksum
from shared.constants import BUFFER_SIZE, FLAG_ACK, FLAG_FIN
from shared.packet_struct import pack_packet, unpack_packet
from shared.rdt_core import RDTTeardownTimeout, reliable_recv, reliable_send


LOOPBACK = "127.0.0.1"


def make_udp_socket() -> socket.socket:
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((LOOPBACK, 0))
    return udp_socket


class FinAckDroppingSocket:
    def __init__(self, real_socket: socket.socket, drops: int | None):
        self.sock = real_socket
        self.drops_remaining = drops
        self.fin_ack_drops = 0

    def settimeout(self, timeout: float) -> None:
        self.sock.settimeout(timeout)

    def recvfrom(self, buffer_size: int):
        return self.sock.recvfrom(buffer_size)

    def sendto(self, data: bytes, address: tuple[str, int]):
        packet = unpack_packet(data)
        should_drop = (
            packet["flags"] == FLAG_FIN
            and (self.drops_remaining is None or self.drops_remaining > 0)
        )
        if should_drop:
            if self.drops_remaining is not None:
                self.drops_remaining -= 1
            self.fin_ack_drops += 1
            return len(data)
        return self.sock.sendto(data, address)


class RDTFinHandshakeTests(unittest.TestCase):
    def test_receiver_reacks_fin_when_first_fin_ack_is_lost(self) -> None:
        sender = make_udp_socket()
        receiver_raw = make_udp_socket()
        receiver = FinAckDroppingSocket(receiver_raw, drops=1)
        self.addCleanup(sender.close)
        self.addCleanup(receiver_raw.close)
        payload = b"recover-after-lost-fin-ack" * 40
        result: dict[str, object] = {}

        def receive() -> None:
            result["data"] = reliable_recv(
                receiver,
                expected_peer=sender.getsockname(),
            )

        receive_thread = threading.Thread(target=receive)
        receive_thread.start()
        reliable_send(sender, receiver_raw.getsockname(), payload)
        receive_thread.join(3.0)

        self.assertFalse(receive_thread.is_alive())
        self.assertEqual(result.get("data"), payload)
        self.assertEqual(receiver.fin_ack_drops, 1)

    def test_sender_times_out_when_every_fin_ack_is_lost(self) -> None:
        sender = make_udp_socket()
        receiver_raw = make_udp_socket()
        receiver = FinAckDroppingSocket(receiver_raw, drops=None)
        self.addCleanup(sender.close)
        self.addCleanup(receiver_raw.close)
        result: dict[str, object] = {}

        def receive() -> None:
            result["data"] = reliable_recv(
                receiver,
                expected_peer=sender.getsockname(),
            )

        with (
            patch("shared.rdt_core.TIMEOUT", 0.03),
            patch("shared.rdt_core.FIN_LINGER_TIMEOUT", 0.06),
            patch("shared.rdt_core.FIN_MAX_RETRIES", 3),
        ):
            receive_thread = threading.Thread(target=receive)
            receive_thread.start()
            with self.assertRaises(RDTTeardownTimeout):
                reliable_send(sender, receiver_raw.getsockname(), b"bounded-timeout")
            receive_thread.join(2.0)

        self.assertFalse(receive_thread.is_alive())
        self.assertEqual(result.get("data"), b"bounded-timeout")
        self.assertEqual(receiver.fin_ack_drops, 3)

    def test_early_fin_receives_cumulative_ack_and_transfer_continues(self) -> None:
        sender = make_udp_socket()
        receiver = make_udp_socket()
        self.addCleanup(sender.close)
        self.addCleanup(receiver.close)
        payload = b"payload-after-early-fin"
        result: dict[str, object] = {}

        def receive() -> None:
            result["data"] = reliable_recv(
                receiver,
                expected_peer=sender.getsockname(),
            )

        receive_thread = threading.Thread(target=receive)
        receive_thread.start()

        sender.sendto(
            pack_packet(seq=1, ack=0, flags=FLAG_FIN),
            receiver.getsockname(),
        )
        sender.settimeout(1.0)
        response, response_peer = sender.recvfrom(BUFFER_SIZE)
        response_packet = unpack_packet(response)

        self.assertEqual(response_peer, receiver.getsockname())
        self.assertTrue(verify_checksum(response))
        self.assertEqual(response_packet["flags"], FLAG_ACK)
        self.assertEqual(response_packet["ack"], 0)

        reliable_send(sender, receiver.getsockname(), payload)
        receive_thread.join(3.0)
        self.assertFalse(receive_thread.is_alive())
        self.assertEqual(result.get("data"), payload)


if __name__ == "__main__":
    unittest.main()
