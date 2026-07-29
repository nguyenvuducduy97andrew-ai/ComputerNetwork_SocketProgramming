"""Client entry point for the Hybrid FTP application."""

import argparse
import socket
import sys

from client.control.client_control import ControlConnection, parse_reply
from client.control.command_handler import handle_command
from client.control.context import ClientContext


def parse_command_line(
    user_input: str,
) -> tuple[str, str | None]:
    parts = user_input.split(maxsplit=1)

    command = parts[0].upper()
    args = parts[1].strip() if len(parts) > 1 else None

    return command, args


def run_client(
    host: str = "localhost",
    port: int = 2121,
) -> None:
    print("Initializing Hybrid FTP Client...")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        try:
            tcp_socket.connect((host, port))
        except OSError as exc:
            print(
                f"Cannot connect to server at "
                f"{host}:{port}: {exc}"
            )
            return
        print(f"Connected to server at {host}:{port}")
        
        control = ControlConnection(tcp_socket)

        try:
            greeting = control.receive_server_greeting()
        except (ConnectionError, OSError) as exc:
            print(f"Cannot receive greeting from server: {exc}")
            return

        print(greeting)

        greeting_code, _ = parse_reply(greeting)

        if greeting_code != 220:
            print("Server is not ready.")
            return

        print(
            "Initializing Hybrid FTP Client... "
            "Enter FTP commands to interact with the server. "
            "Type QUIT to exit."
        )

        context = ClientContext(server_host=host)

        while True:
            try:
                user_input = input("ftp> ").strip()
            except EOFError:
                print("\nExiting Hybrid FTP Client.")
                break
            except KeyboardInterrupt:
                print("\nExiting Hybrid FTP Client.")
                break

            if not user_input:
                continue

            command, args = parse_command_line(user_input)

            try:
                should_continue = handle_command(
                    control,
                    context,
                    command,
                    args,
                )
            except (ConnectionError, OSError) as exc:
                print(f"Error connecting to server: {exc}")
                break

            if not should_continue:
                break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Hybrid FTP client"
    )
    

    parser.add_argument(
        "--host",
        default="localhost",
        help="Server host to connect to",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=2121,
        help="Server TCP port to connect to",
    )

    arguments = parser.parse_args(sys.argv[1:])

    run_client(
        host=arguments.host,
        port=arguments.port,
    )
