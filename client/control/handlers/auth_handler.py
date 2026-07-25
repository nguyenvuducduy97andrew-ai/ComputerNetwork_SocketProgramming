"""Client-side handlers for authentication commands."""


from client.control.client_control import ControlConnection
from client.control.handlers.common import send_and_print


def handle_user(control: ControlConnection, args: str | None) -> bool:
    username = args.strip() if args else ""
    if not username:
        print("Thiếu tên người dùng cho lệnh USER.")
        return True

    send_and_print(control, f"USER {username}")
    return True


def handle_pass(control: ControlConnection, args: str | None) -> bool:
    password = args.strip() if args else ""
    if not password:
        print("Thiếu mật khẩu cho lệnh PASS.")
        return True

    send_and_print(control, f"PASS {password}")
    return True


def handle_quit(control: ControlConnection) -> bool:
    send_and_print(control, "QUIT")
    return False
