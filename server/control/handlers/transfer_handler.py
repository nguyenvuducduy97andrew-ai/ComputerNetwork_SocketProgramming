from server.control.ftp_codes import FTPReplyCode
from server.control.session import ClientSession

# Xử lý các lệnh liên quan đến truyền file: RETR, STOR
#RETR: Retrieve a file from the server
#STOR: Store a file on the server
def handle_retr(session: ClientSession, args: str | None) -> str:
    if not args:
        return FTPReplyCode.SYNTAX_ERROR.format("Missing filename argument.")

    file_path = session.get_absolute_current_directory() / args

    if not file_path.exists() or not file_path.is_file():
        return FTPReplyCode.FILE_UNAVAILABLE.format("File does not exist.")

    # Cài đặt trạng thái truyền file trong session
    session.start_transfer(file_path, direction="RETR")
    return FTPReplyCode.COMMAND_OK.format(f"Ready to send {args}.")

def handle_stor(session: ClientSession, args: str | None) -> str:
    if not args:
        return FTPReplyCode.SYNTAX_ERROR.format("Missing filename argument.")

    file_path = session.get_absolute_current_directory() / args
    # Kiểm tra xem file_path có nằm trong server_root không
    if not str(file_path).startswith(str(session.server_root.resolve())):
        return FTPReplyCode.FILE_UNAVAILABLE.format("Access denied.")

    # Cài đặt trạng thái truyền file trong session
    session.start_transfer(file_path, direction="STOR")
    return FTPReplyCode.COMMAND_OK.format(f"Ready to receive {args}.")