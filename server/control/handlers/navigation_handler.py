from server.control.ftp_codes import FTPReplyCode
from server.control.session import ClientSession

# Xử lý các lệnh liên quan đến điều hướng thư mục: PWD, CWD, CDUP
#PWD: Print Working Directory
#CWD: Change Working Directory
#CDUP: Change to Parent Directory

#Hàm validate_directory kiểm tra xem thư mục được chỉ định có tồn tại và có quyền truy cập hay không.
#Nó cũng đảm bảo rằng thư mục đó nằm trong thư mục gốc của máy chủ (server_root) để ngăn chặn truy cập trái phép.
def validate_directory(session: ClientSession, directory: str) -> bool:
    new_directory = (session.get_absolute_current_directory() / directory).resolve()

    # Kiểm tra xem new_directory có tồn tại và là một thư mục không
    if not new_directory.exists() or not new_directory.is_dir():
        return False

    # Kiểm tra xem new_directory có nằm trong server_root không
    if not str(new_directory).startswith(str(session.server_root.resolve())):
        return False

    return True

def handle_pwd(session: ClientSession) -> str:
    print(f"[navigation_handler] Handling PWD command. Current directory: {session.get_display_current_directory()}")
    current_directory = session.get_display_current_directory()
    return FTPReplyCode.PATH_CREATED.format(f'"{current_directory}"')

def handle_cwd(session: ClientSession, args: str | None) -> str:
    print(f"[navigation_handler] Handling CWD command for directory: {args!r}")
    if not args:
        return FTPReplyCode.SYNTAX_ERROR.format("Missing directory argument.")

    if not validate_directory(session, args):
        return FTPReplyCode.FILE_UNAVAILABLE.format("Directory does not exist or access denied.")
    new_directory = (session.get_absolute_current_directory() / args).resolve()

    # Cập nhật current_directory
    session.current_directory = new_directory.relative_to(session.server_root.resolve())
    return FTPReplyCode.COMMAND_OK.format(f"Changed working directory to {session.get_display_current_directory()}")

def handle_cdup(session: ClientSession) -> str:
    parent_directory = session.get_absolute_current_directory().parent
    # Kiểm tra xem parent_directory có tồn tại và là một thư mục không
    if not validate_directory(session, parent_directory.name):
        return FTPReplyCode.FILE_UNAVAILABLE.format("Parent directory does not exist or access denied.")

    # Cập nhật current_directory
    session.current_directory = parent_directory.relative_to(session.server_root.resolve())
    return FTPReplyCode.COMMAND_OK.format(f"Changed working directory to {session.get_display_current_directory()}")