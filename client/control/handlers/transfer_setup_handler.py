"""Client-side handlers for transfer setup commands."""



from client.control.client_control import ControlConnection
from client.control.handlers.common import send_and_print


def handle_type(control: ControlConnection, args: str | None) -> bool:
    value = args.strip().upper() if args else ""
    if value not in {"A", "I"}:
        print("TYPE command only accepts A or I.")
        return True

    send_and_print(control, f"TYPE {value}")
    return True


def handle_mode(control: ControlConnection, args: str | None) -> bool:
    value = args.strip().upper() if args else ""
    if value not in {"S", "B", "C"}:
        print("MODE command only accepts S, B or C.")
        return True

    send_and_print(control, f"MODE {value}")
    return True
