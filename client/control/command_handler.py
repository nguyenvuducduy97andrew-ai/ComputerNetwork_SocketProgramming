"""Client-side FTP command dispatcher."""

from client.control.client_control import ControlConnection
from client.control.handlers.auth_handler import handle_pass, handle_quit, handle_user
from client.control.handlers.navigation_handler import handle_cdup, handle_cwd, handle_pwd, handle_list, handle_nlst, handle_stat, handle_size, handle_mdtm
from client.control.handlers.transfer_handler import handle_retr, handle_stor, handle_stou, handle_appe, handle_abor
from client.control.handlers.file_handler import handle_dele, handle_rnfr, handle_rnto, handle_hash
from client.control.handlers.transfer_setup_handler import handle_mode, handle_pasv, handle_port, handle_type
from client.control.context import ClientContext
from client.control.handlers.common import handle_help, handle_noop
from client.control.handlers.navigation_handler import handle_mkd, handle_rmd


def handle_command(
    control: ControlConnection,
    context: ClientContext,
    command: str,
    args: str | None,
) -> bool:
    command = command.upper()
#=====================Pre-logging========================
    if command == "USER":
        return handle_user(control, context, args)

    if command == "PASS":
        return handle_pass(control, context, args)

    if command == "HELP":
        return handle_help(control, args)

    if command == "NOOP":
        return handle_noop(control)

    if command == "QUIT":
        return handle_quit(control, context)

    if context.authenticated is False:
        print("Please log in first using USER and PASS commands.")
        return True
#====================Directory and file-information========================
    if command == "PWD":
        return handle_pwd(control)

    if command == "CWD":
        return handle_cwd(control, args)

    if command == "CDUP":
        return handle_cdup(control)

    if command == "MKD":
        return handle_mkd(control, args)

    if command == "RMD":
        return handle_rmd(control, args)


    if command == "LIST":
        return handle_list(control, context, args)

    if command == "NLST":
        return handle_nlst(control, args)

    if command == "STAT":
        return handle_stat(control, args)

    if command == "SIZE":
        return handle_size(control, args)

    if command == "MDTM":
        return handle_mdtm(control, args)

#====================Transfer Setup========================

    if command == "TYPE":
        return handle_type(control, context, args)

    if command == "MODE":
        return handle_mode(control, context, args)

    if command == "PORT":
        return handle_port(control, context, args)

    if command == "PASV":
        return handle_pasv(control, context, args)

    #====================File Transfer========================

    if command == "RETR":
        return handle_retr(control, context, args)

    if command == "STOR":
        return handle_stor(control, context, args)

    if command == "STOU":
        return handle_stou(control, context, args)

    if command == "APPE":
        return handle_appe(control, context, args)

    if command == "ABOR":
        return handle_abor(control)

    #====================File Management========================

    if command == "DELE":
        return handle_dele(control, args)

    if command == "RNFR":
        return handle_rnfr(control, args)

    if command == "RNTO":
        return handle_rnto(control, args)

    if command == "HASH":
        return handle_hash(control, args)


    print(f"Invalid command: {command}")
    return True
