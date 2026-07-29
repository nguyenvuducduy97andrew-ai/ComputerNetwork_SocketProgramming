from server.control.ftp_codes import FTPReplyCode
from server.control.handlers.navigation_handler import resolve_session_path
from server.control.session import ClientSession
from shared.checksum import compute_file_hash

#Handle các lệnh: DELE, RNFR, RNTO, HASH
#DELE: DELE là lệnh để xóa một tập tin trên máy chủ.
#RNFR: RNFR là lệnh để chỉ định tập tin cần đổi tên (Rename From)
#RNTO: RNTO là lệnh để chỉ định tên mới cho tập tin (Rename To)
#HASH: HASH là lệnh để tính toán và trả về giá trị băm (hash) của một tập tin trên máy chủ.
# Giá trị băm có thể được sử dụng để kiểm tra tính toàn vẹn của tập tin sau khi truyền tải.


#=========Handle DELE command=========

def handle_dele(session: ClientSession, args: str | None) -> str:
    print(f"[file_handler] Handling DELE command for file: {args!r}")
    if not args:
        return FTPReplyCode.INVALID_PARAMETER.format("Missing file argument.")

    file_path = resolve_session_path(session, args)

    if file_path is None:
        return FTPReplyCode.FILE_UNAVAILABLE.format("Access denied.")

    if not file_path.exists() or not file_path.is_file():
        return FTPReplyCode.FILE_UNAVAILABLE.format("File does not exist.")

    try:
        file_path.unlink()
        return FTPReplyCode.FILE_ACTION_OK.format(f"Deleted file {file_path.name}.")
    except Exception as e:
        return FTPReplyCode.FILE_UNAVAILABLE.format(f"Failed to delete file: {e}")


#========Handle RNFR and RNTO commands=========

def handle_rnfr(session: ClientSession, args: str | None) -> str:
    print(f"[file_handler] Handling RNFR command for file: {args!r}")
    if not args:
        return FTPReplyCode.INVALID_PARAMETER.format("Missing file argument.")

    file_path = resolve_session_path(session, args)

    if file_path is None:
        return FTPReplyCode.FILE_UNAVAILABLE.format("Access denied.")

    if not file_path.exists() or not file_path.is_file():
        return FTPReplyCode.FILE_UNAVAILABLE.format("File does not exist.")

    session.pending_rename_path = file_path
    return FTPReplyCode.FILE_ACTION_PENDING.format(f"Ready to rename {file_path.name}. Please provide the new name with RNTO.")


def handle_rnto(session: ClientSession, args: str | None) -> str:
    print(f"[file_handler] Handling RNTO command for new name: {args!r}")
    if not args:
        return FTPReplyCode.INVALID_PARAMETER.format("Missing new name argument.")

    if session.pending_rename_path is None:
        return FTPReplyCode.BAD_COMMAND_SEQUENCE.format("No rename source selected. Use RNFR first.")

    new_file_path = resolve_session_path(session, args)

    if new_file_path is None:
        return FTPReplyCode.FILE_UNAVAILABLE.format("Access denied.")

    try:
        session.pending_rename_path.rename(new_file_path)
        session.reset_rename_state()
        return FTPReplyCode.FILE_ACTION_OK.format(f"Renamed file to {new_file_path.name}.")
    except Exception as e:
        session.reset_rename_state()
        return FTPReplyCode.FILE_UNAVAILABLE.format(f"Failed to rename file: {e}")



#=========Handle HASH command=========

def handle_hash(session: ClientSession, args: str | None) -> str:
    print(f"[file_handler] Handling HASH command for file: {args!r}")

    if not args:
        return FTPReplyCode.INVALID_PARAMETER.format("Missing file argument.")

    file_path = resolve_session_path(session, args)

    if file_path is None:
        return FTPReplyCode.FILE_UNAVAILABLE.format("Access denied.")

    try:
        file_path.relative_to(session.server_root.resolve())
    except ValueError:
        return FTPReplyCode.FILE_UNAVAILABLE.format("Access denied.")

    if not file_path.exists():
        return FTPReplyCode.FILE_UNAVAILABLE.format("File does not exist.")

    if not file_path.is_file():
        return FTPReplyCode.FILE_UNAVAILABLE.format("Target is not a file.")

    try:
        hash_value = compute_file_hash(str(file_path))
        return FTPReplyCode.COMMAND_OK.format(f"SHA-256 {file_path.name} {hash_value}")
    except Exception as e:
        return FTPReplyCode.FILE_UNAVAILABLE.format(f"Failed to compute file hash: {e}")
    
