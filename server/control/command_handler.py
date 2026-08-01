from server.control.ftp_codes import FTPReplyCode
from server.control.command_result import CommandHandlerResult
from server.control.session import ClientSession

# Authentication / common commands
from server.control.handlers.auth_handler import (
    handle_user,
    handle_pass,
    handle_quit,
)
from server.control.handlers.common_handler import (
    handle_noop,
    handle_help,
)

# Directory and file-information commands
from server.control.handlers.navigation_handler import (
    handle_pwd,
    handle_cwd,
    handle_cdup,
    handle_mkd,
    handle_rmd,
    handle_list,
    handle_nlst,
    handle_stat,
    handle_size,
    handle_mdtm,
)

# Transfer configuration and data-channel commands
from server.control.handlers.transfer_setup_handler import (
    handle_type,
    handle_mode,
    handle_port,
    handle_pasv,
)

# File-transfer commands
from server.control.handlers.transfer_handler import (
    handle_retr,
    handle_stor,
    handle_stou,
    handle_appe,
    handle_abor,
)

# File-management commands
from server.control.handlers.file_handler import (
    handle_dele,
    handle_rnfr,
    handle_rnto,
    handle_hash,
)


SUPPORTED_COMMANDS = {
    "USER", "PASS", "QUIT", "NOOP", "HELP",
    "PWD", "CWD", "CDUP", "MKD", "RMD",
    "LIST", "NLST", "STAT", "SIZE", "MDTM",
    "TYPE", "MODE", "PORT", "PASV",
    "RETR", "STOR", "STOU", "APPE", "ABOR",
    "DELE", "RNFR", "RNTO", "HASH",
}
COMMANDS_ALLOWED_DURING_TRANSFER = {
    "ABOR",
    "NOOP",
    "STAT",
    "QUIT",
}


def handle_command(
    session: ClientSession,
    command: str,
    args: str | None,
) -> CommandHandlerResult:
    """
    Dispatch one FTP-like command to the corresponding server handler.

    Commands are received through the TCP control channel. Each handler must
    return a complete FTP reply string, including the three-digit reply code.
    """
    command = command.strip().upper()
    args = args.strip() if args is not None else None

    if args:
        logged_args = "********" if command == "PASS" else args
        print(f"Dispatching server command: {command} {logged_args}")
    else:
        print(f"Dispatching server command: {command}")

    # Check if the command is allowed during a data transfer
    if session.transfer_in_progress and command not in COMMANDS_ALLOWED_DURING_TRANSFER:
        return FTPReplyCode.BAD_COMMAND_SEQUENCE.format("Command rejected: a data transfer is in progress.")

    # ---------------------------------------------------------
    # Commands allowed before authentication
    # ---------------------------------------------------------
    session.record_activity()  # Update last activity timestamp for any command
    if command == "USER":
        print("Routing to authentication handler: USER")
        return handle_user(session, args)

    if command == "PASS":
        print("Routing to authentication handler: PASS")
        return handle_pass(session, args)

    if command == "QUIT":
        print("Routing to common handler: QUIT")
        return handle_quit(session)

    if command == "NOOP":
        print("Routing to common handler: NOOP")
        return handle_noop(session)

    if command == "HELP":
        print("Routing to common handler: HELP")
        return handle_help(session, args)

    if command not in SUPPORTED_COMMANDS:
        print(f"Command not implemented: {command}")
        return FTPReplyCode.COMMAND_NOT_IMPLEMENTED.format(
            f"Command {command} is not implemented. Enter HELP to see available commands."
        )

    

    # All remaining commands require authentication.
    if not session.authenticated:
        return FTPReplyCode.NOT_LOGGED_IN.format("Command rejected: please log in beforehand. Use USER and PASS.")

    # ---------------------------------------------------------
    # Directory navigation and directory management
    # ---------------------------------------------------------

    if command == "PWD":
        print("Routing to navigation handler: PWD")
        return handle_pwd(session)

    if command == "CWD":
        print("Routing to navigation handler: CWD")
        return handle_cwd(session, args)

    if command == "CDUP":
        print("Routing to navigation handler: CDUP")
        return handle_cdup(session)

    if command == "MKD":
        print("Routing to navigation handler: MKD")
        return handle_mkd(session, args)

    if command == "RMD":
        print("Routing to navigation handler: RMD")
        return handle_rmd(session, args)

    # ---------------------------------------------------------
    # Directory listing and metadata
    # ---------------------------------------------------------

    if command == "LIST":
        print("Routing to navigation handler: LIST")
        return handle_list(session, args)

    if command == "NLST":
        print("Routing to navigation handler: NLST")
        return handle_nlst(session, args)

    if command == "STAT":
        print("Routing to navigation handler: STAT")
        return handle_stat(session, args)

    if command == "SIZE":
        print("Routing to navigation handler: SIZE")
        return handle_size(session, args)

    if command == "MDTM":
        print("Routing to navigation handler: MDTM")
        return handle_mdtm(session, args)

    # ---------------------------------------------------------
    # Transfer type, transfer mode, and data-channel mode
    # ---------------------------------------------------------

    if command == "TYPE":
        print("Routing to transfer setup handler: TYPE")
        return handle_type(session, args)

    if command == "MODE":
        print("Routing to transfer setup handler: MODE")
        return handle_mode(session, args)

    if command == "PORT":
        print("Routing to transfer setup handler: PORT")
        return handle_port(session, args)

    if command == "PASV":
        print("Routing to transfer setup handler: PASV")
        return handle_pasv(session)

    # ---------------------------------------------------------
    # File transfer
    # ---------------------------------------------------------

    if command == "RETR":
        print("Routing to transfer handler: RETR")
        return handle_retr(session, args)

    if command == "STOR":
        print("Routing to transfer handler: STOR")
        return handle_stor(session, args)

    if command == "STOU":
        print("Routing to transfer handler: STOU")
        return handle_stou(session)

    if command == "APPE":
        print("Routing to transfer handler: APPE")
        return handle_appe(session, args)

    if command == "ABOR":
        print("Routing to transfer handler: ABOR")
        return handle_abor(session)

    # ---------------------------------------------------------
    # File management and integrity verification
    # ---------------------------------------------------------

    if command == "DELE":
        print("Routing to file handler: DELE")
        return handle_dele(session, args)

    if command == "RNFR":
        print("Routing to file handler: RNFR")
        return handle_rnfr(session, args)

    if command == "RNTO":
        print("Routing to file handler: RNTO")
        return handle_rnto(session, args)

    if command == "HASH":
        print("Routing to file handler: HASH")
        return handle_hash(session, args)

    # ---------------------------------------------------------
    # Unsupported command
    # ---------------------------------------------------------

    print(f"Command not implemented: {command}")
    return FTPReplyCode.COMMAND_NOT_IMPLEMENTED.format(
        f"Command {command} is not implemented. Enter HELP to see available commands."
    )
