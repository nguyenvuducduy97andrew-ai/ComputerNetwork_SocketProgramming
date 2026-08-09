"""High-level orchestration for server-side file and data transfers."""

from pathlib import Path

from server.control.data_channel import (
    open_receive_channel,
    open_send_channel,
    validate_data_connection,
)
from server.control.session import ClientSession
from server.control.transfer_codec import (
    decode_from_transfer,
    encode_for_transfer,
    normalize_transfer_mode,
    normalize_transfer_type,
)
from server.control.transfer_errors import DataTransferError
from shared.rdt_core import reliable_recv, reliable_send


def prepare_outgoing_file_data(
    session: ClientSession,
    file_path: Path,
) -> bytes:
    """Đọc file và chuẩn bị dữ liệu để truyền đi, chuyển đổi sang wire representation dựa trên TYPE/MODE."""
    return encode_for_transfer(
        file_path.read_bytes(),
        session.transfer_type,
        session.transfer_mode,
    )


def send_data(session: ClientSession, data: bytes) -> None:
    """Gửi dữ liệu đã được mã hóa qua kênh dữ liệu đã được thiết lập, xử lý các lỗi có thể xảy ra trong quá trình truyền."""
    try:
        with open_send_channel(session) as channel:
            reliable_send(
                channel.udp_socket,
                channel.peer,
                data,
                cancel_event=session.cancel_event,
            )
    except InterruptedError:
        raise
    except DataTransferError:
        raise
    except Exception as exc:
        raise DataTransferError(
            "Failed to send data through the UDP channel."
        ) from exc


def receive_file(
    session: ClientSession,
    save_file_path: Path,
    append: bool = False,
) -> int:
    """Nhận dữ liệu từ kênh dữ liệu đã được thiết lập, giải mã dựa trên TYPE/MODE, và lưu vào file. Trả về số byte đã nhận được."""
    transfer_type = normalize_transfer_type(session.transfer_type)
    transfer_mode = normalize_transfer_mode(session.transfer_mode)

    with open_receive_channel(session) as channel:
        wire_data = reliable_recv(
            channel.udp_socket,
            cancel_event=session.cancel_event,
            expected_peer=channel.peer,
            respond_to_syn=channel.is_passive,
        )

    data = decode_from_transfer(wire_data, transfer_type, transfer_mode)
    save_file_path.parent.mkdir(parents=True, exist_ok=True)
    file_mode = "ab" if append else "wb"
    with save_file_path.open(file_mode) as file:
        file.write(data)

    session.transferred_bytes = len(data)
    return len(data)
