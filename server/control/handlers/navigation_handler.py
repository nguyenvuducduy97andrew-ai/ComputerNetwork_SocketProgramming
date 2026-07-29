from server.control.ftp_codes import FTPReplyCode
from server.control.session import ClientSession
from server.control.command_result import CommandReplies, CommandReply
from server.control.data_transfer_service import (
    DataTransferError,
    send_data,
    validate_data_connection,
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
#LIST: List files and directories
#NLST: Name List
#STAT: File Status
#SIZE: File Size
#MDTM: Modification Time

def format_list_entry(entry: Path) -> str:
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

def resolve_session_path(session: ClientSession, user_path: str,) -> Path | None:
    server_root = session.server_root.resolve()
    candidate = (session.get_absolute_current_directory() / user_path).resolve()

    try:
        candidate.relative_to(server_root)
    except ValueError:
        return None

    return candidate

#Hàm validate_directory kiểm tra xem thư mục được chỉ định có tồn tại và có quyền truy cập hay không.
#Nó cũng đảm bảo rằng thư mục đó nằm trong thư mục gốc của máy chủ (server_root) để ngăn chặn truy cập trái phép.
def validate_directory(session: ClientSession, directory: str) -> bool:
    new_directory = resolve_session_path(session, directory)

    # Kiểm tra xem new_directory có tồn tại và là một thư mục không
    if new_directory is None or not new_directory.exists() or not new_directory.is_dir():
        return False

    print(f"[navigation_handler] Validated directory: {new_directory}")
    return new_directory.exists() and new_directory.is_dir()



def handle_pwd(session: ClientSession) -> str:
    print(f"[navigation_handler] Handling PWD command. Current directory: {session.get_display_current_directory()}")
    current_directory = session.get_display_current_directory()
    return FTPReplyCode.PATH_CREATED.format(f'"{current_directory}"')

def handle_cwd(session: ClientSession, args: str | None) -> str:
    print(f"[navigation_handler] Handling CWD command for directory: {args!r}")
    if not args:
        return FTPReplyCode.INVALID_PARAMETER.format("Missing directory argument.")

    if not validate_directory(session, args):
        return FTPReplyCode.FILE_UNAVAILABLE.format("Directory does not exist or access denied.")
    new_directory = (session.get_absolute_current_directory() / args).resolve()

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

    new_directory = resolve_session_path(session, args)

    if new_directory is None:
        return FTPReplyCode.FILE_UNAVAILABLE.format("Access denied.")

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

    target_directory = (session.get_absolute_current_directory() / args).resolve()

    # Kiểm tra xem target_directory có tồn tại và là một thư mục không
    if not validate_directory(session, args):
        return FTPReplyCode.FILE_UNAVAILABLE.format("Directory does not exist or access denied.")

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

    if args:
        target_path = resolve_session_path(session, args)
    else:
        target_path = session.get_absolute_current_directory()

    if target_path is None:
        yield CommandReply(FTPReplyCode.FILE_UNAVAILABLE, "Access denied.")
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
        validate_data_connection(session, direction="SEND")
        yield CommandReply(
            FTPReplyCode.PRELIMINARY_OK,
            "Opening data channel for directory listing.",
        )
        send_data(session, listing.encode("utf-8"))
        yield CommandReply(
            FTPReplyCode.TRANSFER_COMPLETE,
            "Directory listing transferred successfully.",
        )
    except DataTransferError as e:
        print(f"[navigation_handler] Data connection error while listing directory: {e}")
        yield CommandReply(FTPReplyCode.CANNOT_OPEN_DATA_CONNECTION, str(e))
    except OSError as e:
        print(f"[navigation_handler] Error listing directory: {e}")
        yield CommandReply(FTPReplyCode.FILE_UNAVAILABLE, "Failed to list directory.")



def handle_nlst(session: ClientSession, args: str | None) -> str:
    print(f"[navigation_handler] Handling NLST command for directory: {args!r}")
    target_directory = session.get_absolute_current_directory()

    if args:
        target_directory = (target_directory / args).resolve()
        if not validate_directory(session, args):
            return FTPReplyCode.FILE_UNAVAILABLE.format("Directory does not exist or access denied.")

    try:
        entries = list(target_directory.iterdir())
        listing = " | ".join(entry.name for entry in entries)
        return FTPReplyCode.COMMAND_OK.format(listing)
    except Exception as e:
        print(f"[navigation_handler] Error listing directory: {e}")
        return FTPReplyCode.FILE_UNAVAILABLE.format("Failed to list directory.")

def handle_stat(session: ClientSession, args: str | None) -> str:
    print(f"[navigation_handler] Handling STAT command for directory: {args!r}")
    target_directory = session.get_absolute_current_directory()

    if args:
        target_directory = (target_directory / args).resolve()
        if not validate_directory(session, args):
            return FTPReplyCode.FILE_UNAVAILABLE.format("Directory does not exist or access denied.")

    try:
        entries = list(target_directory.iterdir())
        listing = " | ".join(entry.name for entry in entries)
        return FTPReplyCode.COMMAND_OK.format(listing)
    except Exception as e:
        print(f"[navigation_handler] Error getting status of directory: {e}")
        return FTPReplyCode.FILE_UNAVAILABLE.format("Failed to get status of directory.")


def handle_size(session: ClientSession, args: str | None) -> str:
    print(f"[navigation_handler] Handling SIZE command for file: {args!r}")
    if not args:
        return FTPReplyCode.INVALID_PARAMETER.format("Missing filename argument.")

    target_file = resolve_session_path(session, args)

    # Kiểm tra xem target_file có tồn tại và là một tệp không
    if target_file is None or not target_file.exists() or not target_file.is_file():
        return FTPReplyCode.FILE_UNAVAILABLE.format("File does not exist or access denied.")

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

    target_file = resolve_session_path(session, args)

    # Kiểm tra xem target_file có tồn tại và là một tệp không
    if target_file is None or not target_file.exists() or not target_file.is_file():
        return FTPReplyCode.FILE_UNAVAILABLE.format("File does not exist or access denied.")

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
