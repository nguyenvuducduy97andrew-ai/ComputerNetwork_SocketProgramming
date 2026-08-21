import socket
import unittest
from collections import deque
from unittest.mock import patch

from client.control.handlers.transfer_handler import _open_passive_peer
from shared.constants import FLAG_ACK, FLAG_DATA, FLAG_FIN, FLAG_SYN
from shared.packet_struct import pack_packet, unpack_packet
from shared.rdt_core import reliable_send
from tests.reporting import VietnameseTestCase


LOOPBACK = "127.0.0.1"


class DroppedFirstProbeSocket:
    def __init__(self, server_address: tuple[str, int]) -> None:
        self.server_address = server_address
        self.probe_count = 0
        self.responses: deque[tuple[bytes, tuple[str, int]]] = deque()

    def settimeout(self, timeout: float) -> None:
        pass

    def sendto(self, data: bytes, address: tuple[str, int]) -> int:
        packet = unpack_packet(data)
        if packet["flags"] == FLAG_SYN:
            self.probe_count += 1
            if self.probe_count == 2:
                self.responses.append((
                    pack_packet(
                        seq=0,
                        ack=0,
                        flags=FLAG_SYN | FLAG_ACK,
                    ),
                    self.server_address,
                ))
        return len(data)

    def recvfrom(self, buffer_size: int):
        if self.responses:
            return self.responses.popleft()
        raise socket.timeout


class PassiveSenderSocket:
    def __init__(self, client_address: tuple[str, int]) -> None:
        self.client_address = client_address
        self.sent_packets: list[bytes] = []
        self.responses = deque([
            (
                pack_packet(seq=0, ack=0, flags=FLAG_SYN),
                client_address,
            ),
            (
                pack_packet(seq=0, ack=1, flags=FLAG_ACK),
                client_address,
            ),
            (
                pack_packet(seq=0, ack=1, flags=FLAG_FIN),
                client_address,
            ),
        ])

    def settimeout(self, timeout: float) -> None:
        pass

    def sendto(self, data: bytes, address: tuple[str, int]) -> int:
        self.sent_packets.append(data)
        return len(data)

    def recvfrom(self, buffer_size: int):
        if self.responses:
            return self.responses.popleft()
        raise socket.timeout


class PassiveHandshakeRetryTests(VietnameseTestCase):
    suite_title = "PASSIVE HANDSHAKE RETRY"

    def test_client_retries_when_the_first_probe_is_lost(self) -> None:
        """Client gửi lại SYN probe nếu lần đầu bị mất trên Wi-Fi"""
        server_address = (LOOPBACK, 2122)
        data_socket = DroppedFirstProbeSocket(server_address)

        with (
            patch(
                "client.control.handlers.transfer_handler.PASSIVE_HANDSHAKE_TIMEOUT",
                0.005,
            ),
            patch(
                "client.control.handlers.transfer_handler.PASSIVE_HANDSHAKE_RETRIES",
                3,
            ),
        ):
            peer = _open_passive_peer(data_socket, server_address)

        self.assertEqual(peer, server_address)
        self.assertEqual(data_socket.probe_count, 2)

    def test_passive_sender_replies_to_a_retried_probe(self) -> None:
        """Server gửi lại SYN-ACK nếu SYN-ACK đầu tiên bị mất"""
        client_address = (LOOPBACK, 50000)
        data_socket = PassiveSenderSocket(client_address)

        reliable_send(
            data_socket,
            client_address,
            b"payload",
            respond_to_syn=True,
        )

        sent_flags = [
            unpack_packet(packet)["flags"]
            for packet in data_socket.sent_packets
        ]
        self.assertIn(FLAG_DATA, sent_flags)
        self.assertIn(FLAG_SYN | FLAG_ACK, sent_flags)
        self.assertIn(FLAG_FIN, sent_flags)


if __name__ == "__main__":
    unittest.main()
