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

    if args:
        print(f"Dispatching server command: {command} {args}")
    else:
        print(f"Dispatching server command: {command}")

    if command == "USER":
        print("Routing to handler: USER")
        return handle_user(session, args)

    if command == "PASS":
        print("Routing to handler: PASS")
        return handle_pass(session, args)

    if command == "QUIT":
        print("Routing to handler: QUIT")
        return handle_quit(session)

    if not session.authenticated:
        print("Command rejected: client is not logged in")
        return FTPReplyCode.NOT_LOGGED_IN.format()

    if command == "PWD":
        print("Routing to navigation handler: PWD")
        return handle_pwd(session)

    if command == "CWD":
        print("Routing to navigation handler: CWD")
        return handle_cwd(session, args)

    if command == "CDUP":
        print("Routing to navigation handler: CDUP")
        return handle_cdup(session)

    if command == "TYPE":
        print("Routing to transfer setup handler: TYPE")
        return handle_type(session, args)

    if command == "MODE":
        print("Routing to transfer setup handler: MODE")
        return handle_mode(session, args)

    if command == "RETR":
        print("Routing to transfer handler: RETR")
        return handle_retr(session, args)

    if command == "STOR":
        print("Routing to transfer handler: STOR")
        return handle_stor(session, args)

    print(f"Command not implemented: {command}")
    return FTPReplyCode.COMMAND_NOT_IMPLEMENTED.format(
        f"Command {command} is not implemented."
    )
