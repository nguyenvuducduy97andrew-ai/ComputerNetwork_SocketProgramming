from server.control.ftp_codes import FTPReplyCode
from server.control.session import ClientSession

# Xử lý các lệnh liên quan đến điều hướng thư mục: PWD, CWD, CDUP
#PWD: Print Working Directory
#CWD: Change Working Directory
#CDUP: Change to Parent Directory

def handle_pwd(session: ClientSession) -> str:
    current_directory = session.get_display_current_directory()
    return FTPReplyCode.PATH_CREATED.format(f'"{current_directory}"')

def handle_cwd(session: ClientSession, args: str | None) -> str:
    if not args:
        return FTPReplyCode.SYNTAX_ERROR.format("Missing directory argument.")

    new_directory = (session.get_absolute_current_directory() / args).resolve()

    # Kiểm tra xem new_directory có nằm trong server_root không
    if not str(new_directory).startswith(str(session.server_root.resolve())):
        return FTPReplyCode.FILE_UNAVAILABLE.format("Access denied.")

    if not new_directory.is_dir():
        return FTPReplyCode.FILE_UNAVAILABLE.format("Directory does not exist.")

    # Cập nhật current_directory
    session.current_directory = new_directory.relative_to(session.server_root.resolve())
    return FTPReplyCode.COMMAND_OK.format(f"Changed working directory to {session.get_display_current_directory()}")

def handle_cdup(session: ClientSession) -> str:
    parent_directory = session.get_absolute_current_directory().parent

    # Kiểm tra xem parent_directory có nằm trong server_root không
    if not str(parent_directory).startswith(str(session.server_root.resolve())):
        return FTPReplyCode.FILE_UNAVAILABLE.format("Access denied.")

    # Cập nhật current_directory
    session.current_directory = parent_directory.relative_to(session.server_root.resolve())
    return FTPReplyCode.COMMAND_OK.format(f"Changed working directory to {session.get_display_current_directory()}")