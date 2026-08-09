"""Active/passive UDP channel setup and lifecycle management."""

import socket
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from server.control.session import ClientSession
from server.control.transfer_errors import DataTransferError
from shared.checksum import verify_checksum
from shared.constants import BUFFER_SIZE, FLAG_ACK, FLAG_SYN, HEADER_SIZE
from shared.packet_struct import pack_packet, unpack_packet


ACTIVE_HANDSHAKE_TIMEOUT = 1.0
ACTIVE_HANDSHAKE_RETRIES = 5
PASSIVE_DISCOVERY_TIMEOUT = 5.0


@dataclass(frozen=True)
class DataChannel:
    udp_socket: socket.socket
    peer: tuple[str, int]
    mode: str

    @property
    def is_passive(self) -> bool:
        return self.mode == "PASSIVE"


def validate_data_connection(session: ClientSession) -> None:
    """Validate data-channel configuration without opening a channel."""
    if session.data_connection_mode == "PASSIVE":
        if session.passive_udp_socket is None:
            raise DataTransferError(
                "Passive UDP socket is not available. Use PASV before transferring data."
            )
        return

    if session.data_connection_mode == "ACTIVE":
        if session.active_udp_address is None:
            raise DataTransferError(
                "Active data address is not configured. Use PORT before transferring data."
            )
        return

    raise DataTransferError(
        "Data connection mode is not selected. Use PORT or PASV before transferring data."
    )


def _raise_if_cancelled(session: ClientSession) -> None:
    if session.cancel_event.is_set():
        raise InterruptedError("Transfer aborted.")


def _unpack_valid_packet(packet_bytes: bytes) -> dict | None:
    if len(packet_bytes) < HEADER_SIZE or not verify_checksum(packet_bytes):
        return None
    try:
        return unpack_packet(packet_bytes)
    except ValueError:
        return None


def _discover_passive_peer(
    session: ClientSession,
    udp_socket: socket.socket,
) -> tuple[str, int]:
    deadline = time.monotonic() + PASSIVE_DISCOVERY_TIMEOUT

    while True:
        _raise_if_cancelled(session)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise DataTransferError(
                "Timed out while waiting for the client in passive mode."
            )

        udp_socket.settimeout(remaining)
        try:
            response, client_address = udp_socket.recvfrom(BUFFER_SIZE)
        except socket.timeout as exc:
            raise DataTransferError(
                "Timed out while waiting for the client in passive mode."
            ) from exc

        if client_address[0] != session.client_address[0]:
            continue

        packet = _unpack_valid_packet(response)
        if packet is None:
            continue
        if (
            packet["flags"] != FLAG_SYN
            or packet["length"] != 0
            or packet["payload"] != b""
        ):
            continue

        session.passive_client_address = client_address
        syn_ack = pack_packet(seq=0, ack=0, flags=FLAG_SYN | FLAG_ACK)
        udp_socket.sendto(syn_ack, client_address)
        return client_address


def _open_active_receive_peer(
    session: ClientSession,
    udp_socket: socket.socket,
    client_address: tuple[str, int],
) -> tuple[str, int]:
    udp_socket.bind(("", 0))
    syn_packet = pack_packet(seq=0, ack=0, flags=FLAG_SYN)

    for _ in range(ACTIVE_HANDSHAKE_RETRIES):
        _raise_if_cancelled(session)
        udp_socket.sendto(syn_packet, client_address)
        udp_socket.settimeout(ACTIVE_HANDSHAKE_TIMEOUT)

        try:
            response, sender_address = udp_socket.recvfrom(BUFFER_SIZE)
        except socket.timeout:
            continue

        if sender_address != client_address:
            continue

        packet = _unpack_valid_packet(response)
        if packet is None:
            continue
        if (
            packet["flags"] == (FLAG_SYN | FLAG_ACK)
            and packet["length"] == 0
            and packet["payload"] == b""
        ):
            return sender_address

    raise DataTransferError("Timed out while opening the active upload channel.")


def _passive_socket(session: ClientSession) -> socket.socket:
    udp_socket = session.passive_udp_socket
    if udp_socket is None:
        raise DataTransferError(
            "Passive UDP socket is not available. Use PASV before transferring data."
        )
    return udp_socket


def _active_peer(session: ClientSession) -> tuple[str, int]:
    peer = session.active_udp_address
    if peer is None:
        raise DataTransferError(
            "Active data address is not configured. Use PORT before transferring data."
        )
    return peer


def _passive_peer(
    session: ClientSession,
    udp_socket: socket.socket,
) -> tuple[str, int]:
    return (
        session.passive_client_address
        or _discover_passive_peer(session, udp_socket)
    )


@contextmanager
def open_send_channel(session: ClientSession) -> Iterator[DataChannel]:
    """Open and manage a UDP channel used by the server as sender."""
    validate_data_connection(session)
    mode = session.data_connection_mode or ""
    is_active = mode == "ACTIVE"
    udp_socket = (
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if is_active
        else _passive_socket(session)
    )
    registered = False

    try:
        session.register_data_socket(udp_socket)
        registered = True
        peer = _active_peer(session) if is_active else _passive_peer(session, udp_socket)
        yield DataChannel(udp_socket, peer, mode)
    finally:
        if registered:
            session.unregister_data_socket(udp_socket)
        if is_active:
            udp_socket.close()


@contextmanager
def open_receive_channel(session: ClientSession) -> Iterator[DataChannel]:
    """Open and manage a UDP channel used by the server as receiver."""
    validate_data_connection(session)
    mode = session.data_connection_mode or ""
    is_active = mode == "ACTIVE"
    udp_socket = (
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if is_active
        else _passive_socket(session)
    )
    registered = False

    try:
        session.register_data_socket(udp_socket)
        registered = True
        peer = (
            _open_active_receive_peer(session, udp_socket, _active_peer(session))
            if is_active
            else _passive_peer(session, udp_socket)
        )
        yield DataChannel(udp_socket, peer, mode)
    finally:
        if registered:
            session.unregister_data_socket(udp_socket)
        if is_active:
            udp_socket.close()
