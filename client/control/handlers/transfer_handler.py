"""Client-side handlers for transfer commands."""



from client.control.client_control import ControlConnection
from client.control.handlers.common import send_and_print


def handle_retr(control: ControlConnection, args: str | None) -> bool:
    filename = args.strip() if args else ""
    if not filename:
        print("Missing filename for RETR command.")
        return True

    send_and_print(control, f"RETR {filename}")
    return True


def handle_stor(control: ControlConnection, args: str | None) -> bool:
    filename = args.strip() if args else ""
    if not filename:
        print("Missing filename for STOR command.")
        return True

    send_and_print(control, f"STOR {filename}")
    return True
