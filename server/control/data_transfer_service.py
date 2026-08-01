import os
import socket
import zlib
from pathlib import Path

from server.control.session import ClientSession
from shared.checksum import verify_checksum
from shared.constants import BUFFER_SIZE, FLAG_ACK, FLAG_SYN, HEADER_SIZE
from shared.packet_struct import pack_packet, unpack_packet
from shared.rdt_core import reliable_recv, reliable_send


class DataTransferError(Exception):
    """Lỗi cấu hình hoặc thực thi data channel."""


ACTIVE_HANDSHAKE_TIMEOUT = 1.0
ACTIVE_HANDSHAKE_RETRIES = 5


def _raise_if_transfer_cancelled(session: ClientSession) -> None:
    if session.cancel_event.is_set():
        raise InterruptedError("Transfer aborted.")


def _get_transfer_type(session: ClientSession) -> str:
    transfer_type = session.transfer_type.upper()

    if transfer_type not in ("A", "I"):
        raise DataTransferError(f"Unsupported transfer type: {transfer_type}")

    return transfer_type


def _get_transfer_mode(session: ClientSession) -> str:
    transfer_mode = session.transfer_mode.upper()

    if transfer_mode not in ("S", "B", "C"):
        raise DataTransferError(f"Unsupported transfer mode: {transfer_mode}")

    return transfer_mode


def _create_active_udp_socket() -> socket.socket:
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def validate_data_connection(
    session: ClientSession,
    *,
    direction: str,
) -> None:
    """Validate data-channel configuration without starting a transfer."""
    normalized_direction = direction.upper()

    if normalized_direction not in {"SEND", "RECEIVE"}:
        raise ValueError(f"Unsupported data direction: {direction}")

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

def _discover_passive_client(
    session: ClientSession,
) -> tuple[str, int]:
    udp_socket = session.passive_udp_socket

    if udp_socket is None:
        raise DataTransferError(
            "Passive UDP socket is not available. Use PASV first."
        )

    udp_socket.settimeout(5.0)

    try:
        _, client_address = udp_socket.recvfrom(2048)
    except socket.timeout as exc:
        raise DataTransferError(
            "Timed out waiting for the client's passive UDP probe."
        ) from exc

    if client_address[0] != session.client_address[0]:
        raise DataTransferError(
            "Passive UDP probe came from an unexpected host."
        )

    session.passive_client_address = client_address
    return client_address


def _resolve_send_channel(session: ClientSession) -> tuple[socket.socket, tuple[str, int], bool]:
    """
    Trả về:
        udp_socket
        destination_address
        should_close_socket
    """

    validate_data_connection(session, direction="SEND")

    if session.data_connection_mode == "ACTIVE":
        if session.active_udp_address is None:
            raise DataTransferError("Active data address is not configured. Use PORT before transferring data.")

        udp_socket = _create_active_udp_socket()
        return udp_socket, session.active_udp_address, True

    if session.data_connection_mode == "PASSIVE":
        if session.passive_udp_socket is None:
            raise DataTransferError("Passive UDP socket is not available. Use PASV before transferring data.")

        client_address = getattr(session, "passive_client_address", None)

        if client_address is None:
            client_address = _discover_passive_client(session)

        return session.passive_udp_socket, client_address, False

    raise DataTransferError("Data connection mode is not selected. Use PORT or PASV before transferring data.")


def _open_active_receive_channel(
    session: ClientSession,
) -> tuple[socket.socket, tuple[str, int]]:
    client_address = session.active_udp_address
    if client_address is None:
        raise DataTransferError(
            "Active data address is not configured. Use PORT before uploading."
        )

    udp_socket = _create_active_udp_socket()

    try:
        udp_socket.bind(("", 0))
        session.register_data_socket(udp_socket)
        udp_socket.settimeout(ACTIVE_HANDSHAKE_TIMEOUT)
        syn_packet = pack_packet(seq=0, ack=0, flags=FLAG_SYN)

        for _ in range(ACTIVE_HANDSHAKE_RETRIES):
            _raise_if_transfer_cancelled(session)
            udp_socket.sendto(syn_packet, client_address)

            try:
                response, sender_address = udp_socket.recvfrom(BUFFER_SIZE)
            except socket.timeout:
                _raise_if_transfer_cancelled(session)
                continue

            if sender_address != client_address:
                continue

            if len(response) < HEADER_SIZE or not verify_checksum(response):
                continue

            packet = unpack_packet(response)
            if (
                packet["flags"] == (FLAG_SYN | FLAG_ACK)
                and packet["length"] == 0
                and packet["payload"] == b""
            ):
                return udp_socket, sender_address

        raise DataTransferError(
            "Timed out while opening the active upload channel."
        )
    except BaseException:
        session.unregister_data_socket(udp_socket)
        udp_socket.close()
        raise


def _resolve_receive_channel(
    session: ClientSession,
) -> tuple[socket.socket, tuple[str, int] | None, bool]:
    """
    Chọn socket dùng để nhận dữ liệu.

    Passive mode dùng passive_udp_socket đã bind.
    Active mode hiện cần quy ước thêm local UDP port phía server.
    """

    validate_data_connection(session, direction="RECEIVE")

    if session.data_connection_mode == "PASSIVE":
        if session.passive_udp_socket is None:
            raise DataTransferError("Passive UDP socket is not available. Use PASV before transferring data.")

        return (
            session.passive_udp_socket,
            session.passive_client_address,
            False,
        )

    if session.data_connection_mode == "ACTIVE":
        udp_socket, client_address = _open_active_receive_channel(session)
        return udp_socket, client_address, True

    raise DataTransferError("Data connection mode is not selected. Use PORT or PASV before transferring data.")


def _read_outgoing_file(file_path: Path, transfer_type: str) -> bytes:
    if transfer_type == "I":
        return file_path.read_bytes()

    try:
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise DataTransferError("File cannot be transferred using TYPE A because it is not valid UTF-8 text.") from exc

    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\r\n")
    return text.encode("utf-8")


def _apply_outgoing_mode(data: bytes, transfer_mode: str) -> bytes:
    if transfer_mode in ("S", "B"):
        return data

    if transfer_mode == "C":
        return zlib.compress(data)

    raise DataTransferError(f"Unsupported transfer mode: {transfer_mode}")


def prepare_outgoing_file_data(
    session: ClientSession,
    file_path: Path,
) -> bytes:
    """Read and transform a file before announcing its wire size."""
    transfer_type = _get_transfer_type(session)
    transfer_mode = _get_transfer_mode(session)
    data = _read_outgoing_file(file_path, transfer_type)
    return _apply_outgoing_mode(data, transfer_mode)


def _apply_incoming_mode(data: bytes, transfer_mode: str) -> bytes:
    if transfer_mode in ("S", "B"):
        return data

    if transfer_mode == "C":
        try:
            return zlib.decompress(data)
        except zlib.error as exc:
            raise DataTransferError("Received compressed data is invalid.") from exc

    raise DataTransferError(f"Unsupported transfer mode: {transfer_mode}")


def _apply_incoming_type(data: bytes, transfer_type: str) -> bytes:
    if transfer_type == "I":
        return data

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DataTransferError("Received TYPE A data is not valid UTF-8 text.") from exc

    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", os.linesep)
    return text.encode("utf-8")


def send_file(session: ClientSession, file_path: Path) -> None:
    """
    Gửi file dựa trên:
    - PORT/PASV
    - TYPE A/I
    - MODE S/B/C
    """

    udp_socket, destination_address, should_close = _resolve_send_channel(session)

    try:
        session.register_data_socket(udp_socket)
        data = prepare_outgoing_file_data(session, file_path)
        reliable_send(udp_socket, destination_address, data)
    finally:
        session.unregister_data_socket(udp_socket)
        if should_close:
            udp_socket.close()


def send_data(session: ClientSession, data: bytes) -> None:
    """Send an in-memory payload through the configured UDP data channel."""
    udp_socket, destination_address, should_close = _resolve_send_channel(session)

    try:
        session.register_data_socket(udp_socket)
        reliable_send(udp_socket, destination_address, data, cancel_event=session.cancel_event)
    except InterruptedError:
        raise
    except Exception as exc:
        raise DataTransferError("Failed to send data through the UDP channel.") from exc
    finally:
        session.unregister_data_socket(udp_socket)
        if should_close:
            udp_socket.close()


def receive_file(session: ClientSession, save_file_path: Path, append: bool = False) -> int:
    """
    Nhận file dựa trên:
    - PORT/PASV
    - TYPE A/I
    - MODE S/B/C

    Trả về số byte thực tế đã ghi.
    """

    udp_socket, expected_peer, should_close = _resolve_receive_channel(session)

    try:
        session.register_data_socket(udp_socket)
        transfer_type = _get_transfer_type(session)
        transfer_mode = _get_transfer_mode(session)
        print(f"[DataTransferService] Receiving file. Transfer type: {transfer_type}, Transfer mode: {transfer_mode}")
        raw_data = reliable_recv(
            udp_socket,
            cancel_event=session.cancel_event,
            expected_peer=expected_peer,
        )
        data = _apply_incoming_mode(raw_data, transfer_mode)
        data = _apply_incoming_type(data, transfer_type)

        save_file_path.parent.mkdir(parents=True, exist_ok=True)
        file_mode = "ab" if append else "wb" #ab: append binary, wb: write binary

        with save_file_path.open(file_mode) as file:
            file.write(data)

        session.transferred_bytes = len(data)
        return len(data)
    finally:
        session.unregister_data_socket(udp_socket)
        if should_close:
            udp_socket.close()
