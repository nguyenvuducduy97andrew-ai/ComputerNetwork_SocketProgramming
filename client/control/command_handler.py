"""Client-side FTP command dispatcher."""

from __future__ import annotations

from client.control.client_control import ControlConnection
from client.control.handlers.auth_handler import handle_pass, handle_quit, handle_user
from client.control.handlers.navigation_handler import handle_cdup, handle_cwd, handle_pwd
from client.control.handlers.transfer_handler import handle_retr, handle_stor
from client.control.handlers.transfer_setup_handler import handle_mode, handle_type


def handle_command(
    control: ControlConnection,
    command: str,
    args: str | None,
) -> bool:
    command = command.upper()

    if command == "USER":
        return handle_user(control, args)

    if command == "PASS":
        return handle_pass(control, args)

    if command == "PWD":
        return handle_pwd(control)

    if command == "CWD":
        return handle_cwd(control, args)

    if command == "CDUP":
        return handle_cdup(control)

    if command == "TYPE":
        return handle_type(control, args)

    if command == "MODE":
        return handle_mode(control, args)

    if command == "RETR":
        return handle_retr(control, args)

    if command == "STOR":
        return handle_stor(control, args)

    if command == "QUIT":
        return handle_quit(control)

    print(f"Invalid command: {command}")
    return True
