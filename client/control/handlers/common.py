"""Common helpers for client-side command handlers."""

from client.control.client_control import ControlConnection, parse_reply


def send_and_print(control: ControlConnection, command: str) -> tuple[int | None, str]:
    control.send_command(command)
    response = control.read_reply_line()
    print(response)
    return parse_reply(response)


def require_argument(command_name: str, args: str | None) -> str | None:
    if not args:
        print(f"Missing argument for command {command_name}.")
        return None

    return args.strip()
