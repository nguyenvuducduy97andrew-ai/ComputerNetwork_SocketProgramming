from server.control.ftp_codes import FTPReplyCode
from server.control.session import ClientSession
from server.control.command_result import CommandReplies, CommandReply
from server.control.data_transfer_service import (
    DataTransferError,
    send_data,
    validate_data_connection,
)
from server.control.filesystem_service import (
    SessionPathError,
    require_directory,
    require_file,
    resolve_session_path,
)

from pathlib import Path
from datetime import datetime, timezone
import stat

# Xử lý các lệnh liên quan đến điều hướng thư mục: PWD, CWD, CDUP
#PWD: Print Working Directory
#CWD: Change Working Directory
#CDUP: Change to Parent Directory
#MKD: Make Directory
#RMD: Remove Directory

#Flow của các lệnh dưới chưa được hoàn thiện:
#LIST: List files and directories
#NLST: Name List
#STAT: File Status
#SIZE: File Size
#MDTM: Modification Time

def format_list_entry(entry: Path) -> str: #Dùng cho LIST command
    """Hàm này nhận một đối tượng Path và trả về một chuỗi định dạng"""
    file_stat = entry.stat()

    permissions = stat.filemode(file_stat.st_mode)
    size = file_stat.st_size
    modified_at = datetime.fromtimestamp(file_stat.st_mtime)
    modified_text = modified_at.strftime("%b %d %H:%M")

    # Windows.
    owner = "owner"
    group = "group"

    return (
        f"{permissions} "
        f"1 "
        f"{owner:<8} "
        f"{group:<8} "
        f"{size:>12} "
        f"{modified_text} "
        f"{entry.name}"
    )

def handle_pwd(session: ClientSession) -> str:
    print(f"[navigation_handler] Handling PWD command. Current directory: {session.get_display_current_directory()}")
    current_directory = session.get_display_current_directory()
    return FTPReplyCode.PATH_CREATED.format(f'"{current_directory}"')

def handle_cwd(session: ClientSession, args: str | None) -> str:
    print(f"[navigation_handler] Handling CWD command for directory: {args!r}")
    if not args:
        return FTPReplyCode.INVALID_PARAMETER.format("Missing directory argument.")

    try:
        new_directory = require_directory(session, args)
    except SessionPathError as exc:
        return FTPReplyCode.FILE_UNAVAILABLE.format(str(exc))

    # Cập nhật current_directory
    session.current_directory = new_directory.relative_to(session.server_root.resolve())
    return FTPReplyCode.FILE_ACTION_OK.format(f"Changed working directory to {session.get_display_current_directory()}")

def handle_cdup(session: ClientSession) -> str:
    print(f"[navigation_handler] Handling CDUP command. Current directory: {session.get_display_current_directory()}")

    server_root = session.server_root.resolve()
    current_directory = session.get_absolute_current_directory()
    parent_directory = current_directory.parent.resolve()

    try:
        relative_parent = parent_directory.relative_to(server_root)
    except ValueError:
        return FTPReplyCode.FILE_UNAVAILABLE.format("Cannot move to parent directory. Already at root.")

    # Kiểm tra trực tiếp parent_directory
    if not parent_directory.exists() or not parent_directory.is_dir():
        return FTPReplyCode.FILE_UNAVAILABLE.format("Parent directory does not exist or access denied.")

    # Cập nhật current_directory
    session.current_directory = relative_parent
    return FTPReplyCode.FILE_ACTION_OK.format(f"Changed working directory to {session.get_display_current_directory()}")

def handle_mkd(session: ClientSession, args: str | None) -> str:
    print(f"[navigation_handler] Handling MKD command for directory: {args!r}")
    if not args:
        return FTPReplyCode.INVALID_PARAMETER.format("Missing directory name argument.")

    try:
        new_directory = resolve_session_path(session, args)
    except SessionPathError as exc:
        return FTPReplyCode.FILE_UNAVAILABLE.format(str(exc))

    try:
        new_directory.mkdir(parents=True, exist_ok=False)
        return FTPReplyCode.PATH_CREATED.format(f'"{new_directory.name}"')
    except FileExistsError:
        return FTPReplyCode.FILE_UNAVAILABLE.format("Directory already exists.")
    except Exception as e:
        print(f"[navigation_handler] Error creating directory: {e}")
        return FTPReplyCode.FILE_UNAVAILABLE.format("Failed to create directory.")

def handle_rmd(session: ClientSession, args: str | None) -> str:
    print(f"[navigation_handler] Handling RMD command for directory: {args!r}")
    if not args:
        return FTPReplyCode.INVALID_PARAMETER.format("Missing directory name argument.")

    try:
        target_directory = require_directory(session, args)
    except SessionPathError as exc:
        return FTPReplyCode.FILE_UNAVAILABLE.format(str(exc))

    try:
        target_directory.rmdir()
        return FTPReplyCode.FILE_ACTION_OK.format(f"Removed directory {target_directory.name}")
    except FileNotFoundError:
        return FTPReplyCode.FILE_UNAVAILABLE.format("Directory does not exist.")
    except OSError:
        return FTPReplyCode.FILE_UNAVAILABLE.format("Directory is not empty or cannot be removed.")
    except Exception as e:
        print(f"[navigation_handler] Error removing directory: {e}")
        return FTPReplyCode.FILE_UNAVAILABLE.format("Failed to remove directory.")

def handle_list(session: ClientSession, args: str | None) -> CommandReplies:
    print(f"[navigation_handler] Handling LIST command for directory: {args!r}")

    try:
        target_path = (
            resolve_session_path(session, args)
            if args
            else session.get_absolute_current_directory()
        )
    except SessionPathError as exc:
        yield CommandReply(FTPReplyCode.FILE_UNAVAILABLE, str(exc))
        return

    if not target_path.exists():
        yield CommandReply(FTPReplyCode.FILE_UNAVAILABLE, "Path does not exist or access denied.")
        return

    try:
        if target_path.is_file():
            entries = [target_path]
        elif target_path.is_dir():
            entries = sorted(target_path.iterdir(), key=lambda entry: entry.name.lower())
        else:
            yield CommandReply(
                FTPReplyCode.FILE_UNAVAILABLE,
                "Target is neither a file nor a directory.",
            )
            return

        listing = "\r\n".join(format_list_entry(entry) for entry in entries)
        listing_data = listing.encode("utf-8")
        validate_data_connection(session)
    except DataTransferError as e:
        yield CommandReply(FTPReplyCode.CANNOT_OPEN_DATA_CONNECTION, str(e))
        return
    except OSError as e:
        yield CommandReply(FTPReplyCode.FILE_UNAVAILABLE, "Failed to list directory.")
        return
    yield CommandReply(
        FTPReplyCode.PRELIMINARY_OK,
        f"Opening data connection for directory listing. BYTES={len(listing_data)}",
    )
    session.start_transfer(command="LIST", file_path=target_path, direction="SEND", expected_size=len(listing_data))
    def worker() -> str:
        try:
            send_data(session, listing_data)
        except DataTransferError as e:
            return FTPReplyCode.TRANSFER_ABORTED.format(str(e))
        except OSError:
            return FTPReplyCode.FILE_UNAVAILABLE.format("Failed to send directory listing.")

        return FTPReplyCode.TRANSFER_COMPLETE.format(f"Directory listing sent. BYTES={len(listing_data)}")
    session.run_transfer(worker)



def handle_nlst(session: ClientSession, args: str | None) -> str:
    print(f"[navigation_handler] Handling NLST command for directory: {args!r}")
    try:
        target_directory = (
            require_directory(session, args)
            if args
            else session.get_absolute_current_directory()
        )
    except SessionPathError as exc:
        return FTPReplyCode.FILE_UNAVAILABLE.format(str(exc))

    try:
        entries = list(target_directory.iterdir())
        listing = " | ".join(entry.name for entry in entries)
        return FTPReplyCode.COMMAND_OK.format(listing)
    except Exception as e:
        print(f"[navigation_handler] Error listing directory: {e}")
        return FTPReplyCode.FILE_UNAVAILABLE.format("Failed to list directory.")

def handle_stat(session: ClientSession, args: str | None) -> str:
    print(f"[navigation_handler] Handling STAT command for path: {args!r}")
    try:
        target_path = (
            resolve_session_path(session, args)
            if args
            else session.get_absolute_current_directory()
        )
    except SessionPathError as exc:
        return FTPReplyCode.FILE_UNAVAILABLE.format(str(exc))

    if not target_path.exists():
        return FTPReplyCode.FILE_UNAVAILABLE.format(
            "Path does not exist or access denied."
        )

    try:
        if target_path.is_file():
            listing = format_list_entry(target_path)
        elif target_path.is_dir():
            entries = sorted(
                target_path.iterdir(),
                key=lambda entry: entry.name.lower(),
            )
            listing = " | ".join(format_list_entry(entry) for entry in entries)
        else:
            return FTPReplyCode.FILE_UNAVAILABLE.format(
                "Target is neither a file nor a directory."
            )
        return FTPReplyCode.COMMAND_OK.format(listing)
    except OSError as exc:
        print(f"[navigation_handler] Error getting status of path: {exc}")
        return FTPReplyCode.FILE_UNAVAILABLE.format("Failed to get path status.")


def handle_size(session: ClientSession, args: str | None) -> str:
    print(f"[navigation_handler] Handling SIZE command for file: {args!r}")
    if not args:
        return FTPReplyCode.INVALID_PARAMETER.format("Missing filename argument.")

    try:
        target_file = require_file(session, args)
    except SessionPathError as exc:
        return FTPReplyCode.FILE_UNAVAILABLE.format(str(exc))

    try:
        size = target_file.stat().st_size
        return FTPReplyCode.FILE_STATUS.format(str(size))
    except Exception as e:
        print(f"[navigation_handler] Error getting size of file: {e}")
        return FTPReplyCode.FILE_UNAVAILABLE.format("Failed to get size of file.")



def handle_mdtm(session: ClientSession, args: str | None) -> str:
    print(f"[navigation_handler] Handling MDTM command for file: {args!r}")
    if not args:
        return FTPReplyCode.INVALID_PARAMETER.format("Missing filename argument.")

    try:
        target_file = require_file(session, args)
    except SessionPathError as exc:
        return FTPReplyCode.FILE_UNAVAILABLE.format(str(exc))

    try:
        modified_at = datetime.fromtimestamp(
            target_file.stat().st_mtime,
            tz=timezone.utc,
        )
        return FTPReplyCode.FILE_STATUS.format(
            modified_at.strftime("%Y%m%d%H%M%S")
        )
    except Exception as e:
        print(f"[navigation_handler] Error getting modification time of file: {e}")
        return FTPReplyCode.FILE_UNAVAILABLE.format("Failed to get modification time of file.")
