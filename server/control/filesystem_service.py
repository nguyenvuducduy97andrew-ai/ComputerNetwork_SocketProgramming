"""Safe filesystem path resolution for one authenticated server session."""

from pathlib import Path

from server.control.session import ClientSession


class SessionPathError(ValueError):
    """Được gọi khi có lỗi xảy ra trong quá trình phân giải đường dẫn tệp cho một phiên làm việc của máy chủ."""


def resolve_session_path(session: ClientSession, user_path: str) -> Path:
    """Hàm này nhận một đường dẫn do người dùng cung cấp và trả về một đối tượng Path tuyệt đối"""
    candidate = (session.get_absolute_current_directory() / user_path).resolve()
    server_root = session.server_root.resolve()
    print (f"[filesystem_service] Resolving user path: {user_path!r} to candidate path: {candidate}")
    try:
        print(f"[filesystem_service] Checking if candidate path {candidate} is within server root {server_root}")
        candidate.relative_to(server_root)
    except ValueError as exc:
        print(f"[filesystem_service] Candidate path {candidate} is outside of server root {server_root}. Raising SessionPathError.")
        raise SessionPathError("Access denied.") from exc

    return candidate


def require_file(session: ClientSession, user_path: str) -> Path:
    """Hàm đảm bảo tính hợp lệ của đường dẫn tệp do người dùng cung cấp và trả về một đối tượng Path """
    path = resolve_session_path(session, user_path)
    if not path.exists() or not path.is_file():
        raise SessionPathError("File does not exist or access denied.")
    return path


def require_directory(session: ClientSession, user_path: str) -> Path:
    """Hàm đảm bảo tính hợp lệ của đường dẫn thư mục do người dùng cung cấp và trả về một đối tượng Path """
    path = resolve_session_path(session, user_path)
    if not path.exists() or not path.is_dir():
        raise SessionPathError("Directory does not exist or access denied.")
    return path
