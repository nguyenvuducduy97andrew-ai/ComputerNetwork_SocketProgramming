from server.control.ftp_codes import FTPReplyCode
from server.control.session import ClientSession

# Xử lý các lệnh liên quan đến thiết lập truyền file: TYPE, MODE
#Type: Type là lệnh để thiết lập loại truyền dữ liệu (ASCII hoặc Binary)
#Mode: Mode là lệnh để thiết lập chế độ truyền dữ liệu (Stream, Block, Compressed)

def handle_type(session: ClientSession, args: str | None) -> str:
    if not args:
        return FTPReplyCode.SYNTAX_ERROR.format("Missing type argument.")

    if args.upper() not in ["A", "I"]:
        return FTPReplyCode.SYNTAX_ERROR.format("Invalid type argument. Use 'A' for ASCII or 'I' for Binary.")

    session.transfer_type = args.upper()
    return FTPReplyCode.COMMAND_OK.format(f"Transfer type set to {session.transfer_type}.")

def handle_mode(session: ClientSession, args: str | None) -> str:
    if not args:
        return FTPReplyCode.SYNTAX_ERROR.format("Missing mode argument.")

    if args.upper() not in ["S", "B", "C"]:
        return FTPReplyCode.SYNTAX_ERROR.format("Invalid mode argument. Use 'S' for Stream, 'B' for Block, or 'C' for Compressed.")
    session.transfer_mode = args.upper()
    return FTPReplyCode.COMMAND_OK.format(f"Transfer mode set to {session.transfer_mode}.")