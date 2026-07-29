"""Client-side handlers for authentication commands."""


from client.control.client_control import ControlConnection
from client.control.context import ClientContext
from client.control.handlers.common import send_and_print


def handle_user(control: ControlConnection, session: ClientContext, args: str | None) -> bool:
    username = args.strip() if args else ""
    if not username:
        print("Missing username for USER command.")
        return True

    session.username = None
    session.authenticated = False
    session.reset_data_connection()

    code, _ = send_and_print(control, f"USER {username}")

    session.username = username if code == 331 else None

    return True


def handle_pass(control: ControlConnection, session: ClientContext, args: str | None) -> bool:
    password = args.strip() if args else ""
    if not password:
        print("Missing password for PASS command.")
        return True

    code, _ = send_and_print(control, f"PASS {password}")
    session.authenticated = code == 230
    return True


def handle_quit(control: ControlConnection, session: ClientContext) -> bool:
    session.reset_data_connection()
    session.username = None
    session.authenticated = False
    send_and_print(control, "QUIT")
    return False
