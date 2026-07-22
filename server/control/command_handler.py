from server.control.ftp_codes import FTPReplyCode
from server.control.session import ClientSession
from server.control.handlers.auth_handler import handle_user, handle_pass, handle_quit
from server.control.handlers.navigation_handler import handle_pwd, handle_cwd, handle_cdup
from server.control.handlers.transfer_setup_handler import handle_type, handle_mode
from server.control.handlers.transfer_handler import handle_retr, handle_stor


def handle_command(
    session: ClientSession,
    command: str,
    args: str | None
) -> str:
    command = command.upper()

    if command == "USER":
        return handle_user(session, args)

    if command == "PASS":
        return handle_pass(session, args)

    if command == "QUIT":
        return handle_quit(session)

    if not session.authenticated:
        return FTPReplyCode.NOT_LOGGED_IN.format()

    if command == "PWD":
        return handle_pwd(session)

    if command == "CWD":
        return handle_cwd(session, args)

    if command == "CDUP":
        return handle_cdup(session)

    if command == "TYPE":
        return handle_type(session, args)

    if command == "MODE":
        return handle_mode(session, args)

    if command == "RETR":
        return handle_retr(session, args)

    if command == "STOR":
        return handle_stor(session, args)

    return FTPReplyCode.COMMAND_NOT_IMPLEMENTED.format(
        f"Command {command} is not implemented."
    )
