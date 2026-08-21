import socket
import unittest
from unittest.mock import patch

from shared.constants import FLAG_DATA
from shared.packet_struct import unpack_packet
from shared.rdt_core import RDTDataTimeout, reliable_recv, reliable_send


class NoAckSocket:
    def __init__(self) -> None:
        self.sent_packets: list[bytes] = []
        self.timeout = 0.0

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def sendto(self, data: bytes, address: tuple[str, int]) -> int:
        self.sent_packets.append(data)
        return len(data)

    def recvfrom(self, buffer_size: int):
        raise socket.timeout


class RDTDataRetryLimitTests(unittest.TestCase):
    def test_sender_stops_after_configured_data_retries(self) -> None:
        udp_socket = NoAckSocket()

        with (
            patch("shared.rdt_core.TIMEOUT", 0.005),
            patch("shared.rdt_core.DATA_MAX_RETRIES", 3),
        ):
            with self.assertRaises(RDTDataTimeout):
                reliable_send(
                    udp_socket,
                    ("127.0.0.1", 65000),
                    b"no-ack",
                )

        data_packets = [
            packet
            for packet in udp_socket.sent_packets
            if unpack_packet(packet)["flags"] == FLAG_DATA
        ]
        self.assertEqual(len(data_packets), 4)  # Initial send + 3 retries.

    def test_receiver_stops_after_consecutive_data_timeouts(self) -> None:
        udp_socket = NoAckSocket()

        with (
            patch("shared.rdt_core.TIMEOUT", 0.005),
            patch("shared.rdt_core.DATA_MAX_RETRIES", 3),
        ):
            with self.assertRaises(RDTDataTimeout):
                reliable_recv(udp_socket)


if __name__ == "__main__":
    unittest.main()
