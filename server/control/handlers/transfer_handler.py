from pathlib import Path
from time import time

from server.control.command_result import CommandReplies, CommandReply
from server.control.data_transfer_service import (
    DataTransferError,
    prepare_outgoing_file_data,
    receive_file,
    send_data,
    validate_data_connection,
)
from server.control.ftp_codes import FTPReplyCode
from server.control.session import ClientSession


def _resolve_safe_path(session: ClientSession, filename: str) -> Path | None:
    server_root = session.server_root.resolve()
    file_path = (session.get_absolute_current_directory() / filename).resolve()

    try:
        file_path.relative_to(server_root)
        return file_path
    except ValueError:
        return None


def handle_retr(session: ClientSession, args: str | None) -> CommandReplies:
    print(f"[transfer_handler] Handling RETR command: {args!r}")

    if not args:
        yield CommandReply(FTPReplyCode.INVALID_PARAMETER, "Missing filename argument.")
        return

    file_path = _resolve_safe_path(session, args)

    if file_path is None:
        yield CommandReply(FTPReplyCode.FILE_UNAVAILABLE, "Access denied.")
        return

    if not file_path.exists() or not file_path.is_file():
        yield CommandReply(FTPReplyCode.FILE_UNAVAILABLE, "File does not exist.")
        return

    try:
        validate_data_connection(session, direction="SEND")
        outgoing_data = prepare_outgoing_file_data(session, file_path)
    except DataTransferError as exc:
        yield CommandReply(FTPReplyCode.CANNOT_OPEN_DATA_CONNECTION, str(exc))
        return
    except OSError:
        yield CommandReply(
            FTPReplyCode.FILE_UNAVAILABLE,
            "Failed to read the requested file.",
        )
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

    file_path = _resolve_safe_path(session, args)

    if file_path is None:
        yield CommandReply(FTPReplyCode.FILE_UNAVAILABLE, "Access denied.")
        return

    try:
        validate_data_connection(session, direction="RECEIVE")
    except DataTransferError as exc:
        yield CommandReply(FTPReplyCode.CANNOT_OPEN_DATA_CONNECTION, str(exc))
        return

    yield CommandReply(
        FTPReplyCode.PRELIMINARY_OK,
        f"Ready to receive {file_path.name}.",
    )

    session.start_transfer("STOR", file_path, direction="UPLOAD")

    def _worker() -> str:
        received_size = receive_file(session, file_path, append=False)
        return FTPReplyCode.TRANSFER_COMPLETE.format(
            f"File {args} received successfully. {received_size} bytes stored."
        )

    session.run_transfer(_worker)


def handle_stou(session: ClientSession) -> CommandReplies:
    print("[transfer_handler] Handling STOU command.")

    unique_filename = f"file_{int(time())}.dat"
    file_path = _resolve_safe_path(session, unique_filename)

    if file_path is None:
        yield CommandReply(FTPReplyCode.FILE_UNAVAILABLE, "Access denied.")
        return

    try:
        validate_data_connection(session, direction="RECEIVE")
    except DataTransferError as exc:
        yield CommandReply(FTPReplyCode.CANNOT_OPEN_DATA_CONNECTION, str(exc))
        return

    yield CommandReply(
        FTPReplyCode.PRELIMINARY_OK,
        f"Ready to receive a uniquely named file as {unique_filename}.",
    )

    session.start_transfer("STOU", file_path, direction="UPLOAD")

    def _worker() -> str:
        received_size = receive_file(session, file_path, append=False)
        return FTPReplyCode.TRANSFER_COMPLETE.format(
            f"File stored as {unique_filename} successfully. {received_size} bytes stored."
        )

    session.run_transfer(_worker)


def handle_appe(session: ClientSession, args: str | None) -> CommandReplies:
    print(f"[transfer_handler] Handling APPE command: {args!r}")

    if not args:
        yield CommandReply(FTPReplyCode.INVALID_PARAMETER, "Missing filename argument.")
        return

    file_path = _resolve_safe_path(session, args)

    if file_path is None:
        yield CommandReply(FTPReplyCode.FILE_UNAVAILABLE, "Access denied.")
        return

    try:
        validate_data_connection(session, direction="RECEIVE")
    except DataTransferError as exc:
        yield CommandReply(FTPReplyCode.CANNOT_OPEN_DATA_CONNECTION, str(exc))
        return

    yield CommandReply(
        FTPReplyCode.PRELIMINARY_OK,
        f"Ready to append data to {file_path.name}.",
    )

    session.start_transfer("APPE", file_path, direction="UPLOAD")

    def _worker() -> str:
        received_size = receive_file(session, file_path, append=True)
        return FTPReplyCode.TRANSFER_COMPLETE.format(
            f"Data appended to {args} successfully. {received_size} bytes appended."
        )

    session.run_transfer(_worker)


def handle_abor(session: ClientSession) -> str:
    print("[transfer_handler] Handling ABOR command.")

    if not session.transfer_in_progress:
        return FTPReplyCode.COMMAND_OK.format("No transfer in progress to abort.")

    session.request_abort()
    return FTPReplyCode.TRANSFER_ABORTED.format("Abort request accepted.")
