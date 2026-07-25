"""Client-side handlers for navigation commands."""


from client.control.client_control import ControlConnection
from client.control.handlers.common import send_and_print


def handle_pwd(control: ControlConnection) -> bool:
    send_and_print(control, "PWD")
    return True


def handle_cwd(control: ControlConnection, args: str | None) -> bool:
    path = args.strip() if args else ""
    if not path:
        print("Missing destination directory for CWD command.")
        return True

    send_and_print(control, f"CWD {path}")
    return True


def handle_cdup(control: ControlConnection) -> bool:
    send_and_print(control, "CDUP")
    return True
