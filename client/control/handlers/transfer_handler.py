"""Client-side handlers for transfer commands."""


from pathlib import Path
import re
import socket
import time

from client.control.cli_monitor import make_progress_callback
from client.control.client_control import ControlConnection, parse_reply
from client.control.data_transfer_service import (
    ClientDataProcessingError,
    prepare_upload_data,
    process_download_data,
)
from client.control.handlers.common import send_and_print
from client.control.context import ClientContext
from shared.checksum import verify_checksum
from shared.constants import BUFFER_SIZE, FLAG_ACK, FLAG_SYN, HEADER_SIZE
from shared.packet_struct import pack_packet, unpack_packet
from shared.rdt_core import reliable_recv, reliable_send


TRANSFER_SIZE_PATTERN = re.compile(r"\bBYTES=(\d+)\b", re.IGNORECASE)
ACTIVE_UPLOAD_HANDSHAKE_TIMEOUT = 6.0


def _send_passive_probe(
    data_socket: socket.socket,
    peer_address: tuple[str, int]
) -> None:
    probe_packet = pack_packet(
        seq=0,
        ack=0,
        flags=FLAG_SYN
    )
    data_socket.sendto(probe_packet, peer_address)


def _validate_transfer_settings(session: ClientContext) -> bool:
    if session.transfer_type not in {"A", "I"}:
        print("Set TYPE before transferring.")
        return False

    if session.transfer_mode not in {"S", "B", "C"}:
        print("Set MODE before transferring.")
        return False

    return True


def _require_download_channel(
    session: ClientContext,
) -> tuple[socket.socket | None, tuple[str, int] | None]:
    if not _validate_transfer_settings(session):
        return None, None

    if session.data_connection_mode == "ACTIVE":
        return session.ensure_data_socket(), None

    if session.data_connection_mode != "PASSIVE" or session.data_peer_address is None:
        print("Configure PORT or PASV before downloading.")
        return None, None

    return session.ensure_data_socket(), session.data_peer_address


def _require_upload_channel(
    session: ClientContext,
) -> tuple[socket.socket | None, tuple[str, int] | None]:
    if not _validate_transfer_settings(session):
        return None, None

    if session.data_connection_mode == "ACTIVE":
        return session.ensure_data_socket(), None

    if session.data_connection_mode != "PASSIVE" or session.data_peer_address is None:
        print("Configure PORT or PASV before uploading.")
        return None, None

    return session.ensure_data_socket(), session.data_peer_address


def _wait_for_active_upload_peer(
    data_socket: socket.socket,
    session: ClientContext,
) -> tuple[str, int]:
    expected_server_ip = socket.gethostbyname(session.server_host)
    deadline = time.monotonic() + ACTIVE_UPLOAD_HANDSHAKE_TIMEOUT

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                "Timed out waiting for the server's active upload SYN."
            )

        data_socket.settimeout(remaining)
        try:
            response, server_address = data_socket.recvfrom(BUFFER_SIZE)
        except socket.timeout as exc:
            raise TimeoutError(
                "Timed out waiting for the server's active upload SYN."
            ) from exc

        if server_address[0] != expected_server_ip:
            continue

        if len(response) < HEADER_SIZE or not verify_checksum(response):
            continue

        packet = unpack_packet(response)
        if (
            packet["flags"] != FLAG_SYN
            or packet["length"] != 0
            or packet["payload"] != b""
        ):
            continue

        syn_ack = pack_packet(
            seq=0,
            ack=0,
            flags=FLAG_SYN | FLAG_ACK,
        )
        data_socket.sendto(syn_ack, server_address)
        return server_address


def _resolve_upload_peer(
    data_socket: socket.socket,
    configured_peer: tuple[str, int] | None,
    session: ClientContext,
) -> tuple[str, int]:
    if session.data_connection_mode == "ACTIVE":
        return _wait_for_active_upload_peer(data_socket, session)

    if configured_peer is None:
        raise RuntimeError("Passive upload peer is not configured.")

    return configured_peer


def _report_upload_channel_failure(
    control: ControlConnection,
    error: BaseException,
) -> None:
    print(f"Could not open upload data channel: {error}")
    try:
        print(control.read_reply_line())
    except (ConnectionError, OSError) as reply_error:
        print(f"Could not read the final transfer reply: {reply_error}")


def _read_preliminary_reply(
    control: ControlConnection,
) -> tuple[bool, str]:
    response = control.read_reply_line()
    print(response)
    code, message = parse_reply(response)
    return code in {125, 150}, message


def _resolve_local_download_path(filename: str) -> Path:
    return Path("data") / "client_downloads" / filename


def _resolve_local_upload_path(filename: str) -> Path:
    direct_path = Path(filename)
    if direct_path.exists() and direct_path.is_file():
        return direct_path

    return Path("data") / "client_downloads" / filename


def handle_retr(control: ControlConnection, session: ClientContext, args: str | None) -> bool:
    filename = args.strip() if args else ""
    if not filename:
        print("Missing filename for RETR command.")
        return True

    data_socket, peer_address = _require_download_channel(session)
    if data_socket is None:
        return True

    download_path = _resolve_local_download_path(filename)
    download_path.parent.mkdir(parents=True, exist_ok=True)

    control.send_command(f"RETR {filename}")

    ready, preliminary_message = _read_preliminary_reply(control)
    if not ready:
        return True

    size_match = TRANSFER_SIZE_PATTERN.search(preliminary_message)
    total_bytes = int(size_match.group(1)) if size_match else None

    if peer_address is not None:
        _send_passive_probe(data_socket, peer_address)
    downloaded_data = reliable_recv(
        data_socket,
        total_bytes=total_bytes,
        progress_callback=(
            make_progress_callback("Download")
            if total_bytes is not None
            else None
        ),
    )

    try:
        processed_data = process_download_data(
            downloaded_data,
            session.transfer_type,
            session.transfer_mode,
        )
        download_path.write_bytes(processed_data)
    except (ClientDataProcessingError, OSError) as error:
        print(f"Could not save downloaded file: {error}")

    response = control.read_reply_line()
    print(response)
    return True


def handle_stor(control: ControlConnection, session: ClientContext, args: str | None) -> bool:
    filename = args.strip() if args else ""
    if not filename:
        print("Missing filename for STOR command.")
        return True

    data_socket, peer_address = _require_upload_channel(session)
    if data_socket is None:
        return True
    upload_path = _resolve_local_upload_path(filename)
    if not upload_path.exists() or not upload_path.is_file():
        print(f"File {upload_path} does not exist for STOR command.")
        return True

    try:
        upload_data = prepare_upload_data(
            upload_path,
            session.transfer_type,
            session.transfer_mode,
        )
    except (ClientDataProcessingError, OSError) as error:
        print(f"Could not prepare upload: {error}")
        return True

    control.send_command(f"STOR {filename}")

    ready, _ = _read_preliminary_reply(control)
    if not ready:
        return True

    try:
        peer_address = _resolve_upload_peer(
            data_socket,
            peer_address,
            session,
        )
    except (OSError, RuntimeError, TimeoutError) as error:
        _report_upload_channel_failure(control, error)
        return True

    reliable_send(
        data_socket,
        peer_address,
        upload_data,
        progress_callback=make_progress_callback("Upload"),
    )

    response = control.read_reply_line()
    print(response)
    return True


def handle_stou(control: ControlConnection, session: ClientContext, args: str | None) -> bool:
    filename = args.strip() if args else ""
    if not filename:
        print("Missing filename for STOU command.")
        return True

    data_socket, peer_address = _require_upload_channel(session)
    if data_socket is None:
        return True

    upload_path = _resolve_local_upload_path(filename)
    if not upload_path.exists() or not upload_path.is_file():
        print(f"File {upload_path} does not exist for STOU command.")
        return True

    try:
        upload_data = prepare_upload_data(
            upload_path,
            session.transfer_type,
            session.transfer_mode,
        )
    except (ClientDataProcessingError, OSError) as error:
        print(f"Could not prepare upload: {error}")
        return True

    control.send_command("STOU")

    ready, _ = _read_preliminary_reply(control)
    if not ready:
        return True

    try:
        peer_address = _resolve_upload_peer(
            data_socket,
            peer_address,
            session,
        )
    except (OSError, RuntimeError, TimeoutError) as error:
        _report_upload_channel_failure(control, error)
        return True

    reliable_send(
        data_socket,
        peer_address,
        upload_data,
        progress_callback=make_progress_callback("Upload"),
    )

    response = control.read_reply_line()
    print(response)
    return True


def handle_appe(control: ControlConnection, session: ClientContext, args: str | None) -> bool:
    filename = args.strip() if args else ""
    if not filename:
        print("Missing filename for APPE command.")
        return True

    data_socket, peer_address = _require_upload_channel(session)
    if data_socket is None:
        return True

    upload_path = _resolve_local_upload_path(filename)
    if not upload_path.exists() or not upload_path.is_file():
        print(f"File {upload_path} does not exist for APPE command.")
        return True

    try:
        upload_data = prepare_upload_data(
            upload_path,
            session.transfer_type,
            session.transfer_mode,
        )
    except (ClientDataProcessingError, OSError) as error:
        print(f"Could not prepare upload: {error}")
        return True

    control.send_command(f"APPE {filename}")

    ready, _ = _read_preliminary_reply(control)
    if not ready:
        return True

    try:
        peer_address = _resolve_upload_peer(
            data_socket,
            peer_address,
            session,
        )
    except (OSError, RuntimeError, TimeoutError) as error:
        _report_upload_channel_failure(control, error)
        return True

    reliable_send(
        data_socket,
        peer_address,
        upload_data,
        progress_callback=make_progress_callback("Upload"),
    )

    response = control.read_reply_line()
    print(response)
    return True

def handle_abor(control: ControlConnection) -> bool:
    send_and_print(control, "ABOR")
    return True
