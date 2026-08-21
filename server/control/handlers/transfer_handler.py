from pathlib import Path
from time import time
from collections.abc import Callable

from server.control.command_result import CommandReplies, CommandReply
from server.control.data_transfer_service import (
    DataTransferError,
    prepare_outgoing_file_data,
    receive_file,
    send_data,
    validate_data_connection,
)
from server.control.ftp_codes import FTPReplyCode
from server.control.filesystem_service import (
    SessionPathError,
    require_file,
    resolve_session_path,
)
from server.control.session import ClientSession


def _start_receive_transfer(
    session: ClientSession,
    *,
    command: str,
    file_path: Path,
    append: bool,
    preliminary_message: str,
    completion_message: Callable[[int], str],
) -> CommandReplies:
    """Xác nhận kênh dữ liệu, gửi phản hồi ban đầu, và bắt đầu nhận dữ liệu từ client. Trả về các phản hồi FTP tương ứng."""
    try:
        validate_data_connection(session)
    except DataTransferError as exc:
        yield CommandReply(FTPReplyCode.CANNOT_OPEN_DATA_CONNECTION, str(exc))
        return

    yield CommandReply(FTPReplyCode.PRELIMINARY_OK, preliminary_message)
    session.start_transfer(command, file_path, direction="UPLOAD")

    def worker() -> str:
        received_size = receive_file(session, file_path, append=append)
        return FTPReplyCode.TRANSFER_COMPLETE.format(
            completion_message(received_size)
        )

    session.run_transfer(worker)


def handle_retr(session: ClientSession, args: str | None) -> CommandReplies:
    print(f"[transfer_handler] Handling RETR command: {args!r}")

    if not args:
        yield CommandReply(FTPReplyCode.INVALID_PARAMETER, "Missing filename argument.")
        return

    try:
        file_path = require_file(session, args)
    except SessionPathError as exc:
        yield CommandReply(FTPReplyCode.FILE_UNAVAILABLE, str(exc))
        return

    try:
        validate_data_connection(session)
        outgoing_data = prepare_outgoing_file_data(session, file_path)
    except DataTransferError as exc:
        yield CommandReply(FTPReplyCode.CANNOT_OPEN_DATA_CONNECTION, str(exc))
        return
    except OSError:
        yield CommandReply(FTPReplyCode.FILE_UNAVAILABLE, "Failed to read the requested file.")
        return

    yield CommandReply(
        FTPReplyCode.PRELIMINARY_OK,
        f"Opening data channel for {file_path.name}. BYTES={len(outgoing_data)}",
    )

    session.start_transfer(
        "RETR",
        file_path,
        direction="DOWNLOAD",
        expected_size=len(outgoing_data),
    )

    def _worker() -> str:
        send_data(session, outgoing_data)
        session.transferred_bytes = len(outgoing_data)
        return FTPReplyCode.TRANSFER_COMPLETE.format(f"File {args} sent successfully.")

    session.run_transfer(_worker)


def handle_stor(session: ClientSession, args: str | None) -> CommandReplies:
    print(f"[transfer_handler] Handling STOR command: {args!r}")

    if not args:
        yield CommandReply(FTPReplyCode.INVALID_PARAMETER, "Missing filename argument.")
        return

    try:
        file_path = resolve_session_path(session, args)
    except SessionPathError as exc:
        yield CommandReply(FTPReplyCode.FILE_UNAVAILABLE, str(exc))
        return

    yield from _start_receive_transfer(
        session,
        command="STOR",
        file_path=file_path,
        append=False,
        preliminary_message=f"Ready to receive {file_path.name}.",
        completion_message=lambda received_size: (
            f"File {args} received successfully. {received_size} bytes stored."
        ),
    )


def handle_stou(session: ClientSession) -> CommandReplies:
    """Hàm xử lý lệnh STOU tạo một tệp duy nhất trên máy chủ và nhận dữ liệu từ client. Trả về các phản hồi FTP tương ứng."""
    print("[transfer_handler] Handling STOU command.")

    unique_filename = f"file_{int(time())}.dat"
    try:
        file_path = resolve_session_path(session, unique_filename)
    except SessionPathError as exc:
        yield CommandReply(FTPReplyCode.FILE_UNAVAILABLE, str(exc))
        return

    yield from _start_receive_transfer(
        session,
        command="STOU",
        file_path=file_path,
        append=False,
        preliminary_message=(
            f"Ready to receive a uniquely named file as {unique_filename}."
        ),
        completion_message=lambda received_size: (
            f"File stored as {unique_filename} successfully. "
            f"{received_size} bytes stored."
        ),
    )


def handle_appe(session: ClientSession, args: str | None) -> CommandReplies:
    print(f"[transfer_handler] Handling APPE command: {args!r}")

    if not args:
        yield CommandReply(FTPReplyCode.INVALID_PARAMETER, "Missing filename argument.")
        return

    try:
        file_path = resolve_session_path(session, args)
    except SessionPathError as exc:
        yield CommandReply(FTPReplyCode.FILE_UNAVAILABLE, str(exc))
        return

    yield from _start_receive_transfer(
        session,
        command="APPE",
        file_path=file_path,
        append=True,
        preliminary_message=f"Ready to append data to {file_path.name}.",
        completion_message=lambda received_size: (
            f"Data appended to {args} successfully. "
            f"{received_size} bytes appended."
        ),
    )


def handle_abor(session: ClientSession) -> str:
    print("[transfer_handler] Handling ABOR command.")

    if not session.transfer_in_progress:
        return FTPReplyCode.COMMAND_OK.format("No transfer in progress to abort.")

    session.request_abort()
    session.close_current_data_socket()
    session.reset_data_connection()
    return FTPReplyCode.TRANSFER_COMPLETE.format("Abort command successful.")
