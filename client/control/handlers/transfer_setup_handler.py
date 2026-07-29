"""Client-side handlers for transfer setup commands."""


import re


PASSIVE_PORT_PATTERN = re.compile(
    r"\bUDP_PORT=(\d{1,5})\b",
    re.IGNORECASE
)

from client.control.client_control import ControlConnection
from client.control.handlers.common import send_and_print
from client.control.context import ClientContext


def handle_type(control: ControlConnection, session: ClientContext, args: str | None) -> bool:
    value = args.strip().upper() if args else ""
    if value not in {"A", "I"}:
        print("TYPE command only accepts A or I.")
        return True

    code, _ = send_and_print(control, f"TYPE {value}")
    if code == 200:
        session.transfer_type = value
    return True


def handle_mode(control: ControlConnection, session: ClientContext, args: str | None) -> bool:
    value = args.strip().upper() if args else ""
    if value not in {"S", "B", "C"}:
        print("MODE command only accepts S, B or C.")
        return True

    code, _ = send_and_print(control, f"MODE {value}")
    if code == 200:
        session.transfer_mode = value
    return True


def handle_port(control: ControlConnection,session: ClientContext,args: str | None) -> bool:
    value = args.strip() if args else ""
    local_port = 0

    if value:
        if not value.isdigit():
            print("Usage: PORT [udp-port]")
            print("UDP port must be a numeric value.")
            return True

        local_port = int(value)

        if not 1 <= local_port <= 65535:
            print("UDP port must be between 1 and 65535.")
            return True

    session.reset_data_connection()

    try:
        data_socket = session.ensure_data_socket(local_port)
    except OSError as error:
        if local_port == 0:
            print(f"Could not create the active UDP socket: {error}")
        else:
            print(f"Could not bind the active UDP socket "f"to port {local_port}: {error}")
        return True

    actual_port = data_socket.getsockname()[1]

    code, _ = send_and_print(control,f"PORT {actual_port}")

    if code is None or code >= 400:
        session.reset_data_connection()
        return True

    session.data_connection_mode = "ACTIVE"
    return True

def handle_pasv(control: ControlConnection,session: ClientContext,args: str | None) -> bool:
    if args and args.strip():
        print("Usage: PASV")
        return True

    session.reset_data_connection()
    code, response = send_and_print(control, "PASV")

    if code != 227:
        return True

    match = PASSIVE_PORT_PATTERN.search(response)

    if match is None:
        print("Server did not return a valid passive UDP port.")
        return True

    server_data_port = int(match.group(1))

    if not 1 <= server_data_port <= 65535:
        print(
            "Server returned an invalid passive UDP port: "
            f"{server_data_port}"
        )
        return True

    try:
        session.ensure_data_socket()
    except OSError as error:
        print(f"Could not create the passive UDP socket: {error}")
        return True

    session.data_connection_mode = "PASSIVE"
    session.data_peer_address = (session.server_host,server_data_port)

    return True
