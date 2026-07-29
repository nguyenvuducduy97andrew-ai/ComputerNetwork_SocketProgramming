"""Common helpers, NOOP and HELP handlers for client-side command handlers."""

from client.control.client_control import ControlConnection, parse_reply


def send_and_print(control: ControlConnection, command: str) -> tuple[int | None, str]:
    control.send_command(command)
    response = control.read_reply_line()
    print(response)
    return parse_reply(response)

def handle_noop(control: ControlConnection) -> bool:
    send_and_print(control, "NOOP")
    return True


def handle_help(
    control: ControlConnection,
    args: str | None,
) -> bool:
    command = f"HELP {args.strip()}" if args and args.strip() else "HELP"
    responses = control.send_command_and_receive_multiline_response(command)

    for response in responses:
        print(response)
    return True
