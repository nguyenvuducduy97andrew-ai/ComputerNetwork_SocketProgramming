from client.control.client_control import ControlConnection
from client.control.handlers.common import send_and_print


def handle_dele(control: ControlConnection, args: str | None) -> bool:
    filename = args.strip() if args else ""
    if not filename:
        print("Missing filename for DELE command.")
        return True

    send_and_print(control, f"DELE {filename}")
    return True


def handle_rnfr(control: ControlConnection, args: str | None) -> bool:
    filename = args.strip() if args else ""
    if not filename:
        print("Missing filename for RNFR command.")
        return True

    send_and_print(control, f"RNFR {filename}")
    return True

def handle_rnto(control: ControlConnection, args: str | None) -> bool:
    filename = args.strip() if args else ""
    if not filename:
        print("Missing filename for RNTO command.")
        return True

    send_and_print(control, f"RNTO {filename}")
    return True

def handle_hash(control: ControlConnection, args: str | None) -> bool:
    filename = args.strip() if args else ""
    if not filename:
        print("Missing filename for HASH command.")
        return True

    send_and_print(control, f"HASH {filename}")
    return True
