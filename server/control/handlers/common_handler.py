from server.control.ftp_codes import FTPReplyCode
from server.control.session import ClientSession


def handle_noop(session: ClientSession) -> str:
    """Handle the NOOP command."""
    return FTPReplyCode.COMMAND_OK.format("NOOP command successful.")

HELP_COMMANDS = {
    "USER": {
        "syntax": "USER <username>",
        "description": "Send the client's username to initiate an authentication session."
    },
    "PASS": {
        "syntax": "PASS <password>",
        "description": "Send the client's password to complete authentication."
    },
    "QUIT": {
        "syntax": "QUIT",
        "description": "Gracefully terminate the control connection and end the session."
    },
    "NOOP": {
        "syntax": "NOOP",
        "description": "Perform no operation. Used as a keep-alive ping to prevent session timeout."
    },
    "HELP": {
        "syntax": "HELP [command]",
        "description": "Return help information for all supported commands or detailed usage for a specific command."
    },

    "PWD": {
        "syntax": "PWD",
        "description": "Print the server's current working directory."
    },
    "CWD": {
        "syntax": "CWD <path>",
        "description": "Change the server's current working directory to the specified path."
    },
    "CDUP": {
        "syntax": "CDUP",
        "description": "Change the server's current working directory to its parent directory."
    },
    "MKD": {
        "syntax": "MKD <dirname>",
        "description": "Create a new directory in the server's current working directory."
    },
    "RMD": {
        "syntax": "RMD <dirname>",
        "description": "Remove an empty directory from the server."
    },

    "LIST": {
        "syntax": "LIST [path]",
        "description": "Return a detailed listing of files and directories, including name, size, type, and permissions."
    },
    "NLST": {
        "syntax": "NLST [path]",
        "description": "Return a plain name-only listing of files and directories."
    },
    "STAT": {
        "syntax": "STAT [path]",
        "description": "Return a detailed status listing for a file or directory."
    },
    "SIZE": {
        "syntax": "SIZE <filename>",
        "description": "Return the exact size in bytes of the specified file."
    },
    "MDTM": {
        "syntax": "MDTM <filename>",
        "description": "Return the UTC modification timestamp in YYYYMMDDhhmmss format."
    },

    "TYPE": {
        "syntax": "TYPE {A | I}",
        "description": "Set the data transfer type. A means ASCII text, while I means Image or Binary."
    },
    "MODE": {
        "syntax": "MODE {S | B | C}",
        "description": "Set the transfer mode. S means Stream, B means Block, and C means Compressed."
    },
    "PORT": {
        "syntax": "PORT <udp-port>",
        "description": "Select Active Mode. The client provides its IP address and UDP port for the server data channel."
    },
    "PASV": {
        "syntax": "PASV",
        "description": "Select Passive Mode. The server opens a UDP data port and returns UDP_PORT=<port>."
    },

    "RETR": {
        "syntax": "RETR <filename>",
        "description": "Download the specified file from the server through the data channel."
    },
    "STOR": {
        "syntax": "STOR <filename>",
        "description": "Upload a file from the client and store it on the server using the specified filename."
    },
    "STOU": {
        "syntax": "STOU <local-file>",
        "description": "Upload a local file using a unique server-generated remote filename."
    },
    "APPE": {
        "syntax": "APPE <filename>",
        "description": "Append uploaded data to an existing file, or create the file if it does not exist."
    },
    "ABOR": {
        "syntax": "ABOR",
        "description": "Abort the current data transfer and reset the data channel."
    },

    "DELE": {
        "syntax": "DELE <filename>",
        "description": "Delete the specified file from the server."
    },
    "RNFR": {
        "syntax": "RNFR <oldname>",
        "description": "Specify the existing file to be renamed. Must be followed by RNTO."
    },
    "RNTO": {
        "syntax": "RNTO <newname>",
        "description": "Complete the rename operation previously started by RNFR."
    },
    "HASH": {
        "syntax": "HASH <filename>",
        "description": "Return the SHA-256 hash used for file integrity verification."
    }
}


def handle_help(
    session: ClientSession,
    args: str | None,
) -> str:
    """Handle HELP and HELP <command>."""

    if args and args.strip():
        command = args.strip().upper()
        help_info = HELP_COMMANDS.get(command)

        if help_info is None:
            return FTPReplyCode.COMMAND_NOT_IMPLEMENTED.format(
                f"No help available for command {command}."
            )

        return FTPReplyCode.HELP_MESSAGE.format_multiline(
            f"{command} command help",
            [
                f"Syntax: {help_info['syntax']}",
                f"Description: {help_info['description']}",
            ],
        )

    return FTPReplyCode.HELP_MESSAGE.format_multiline(
        "Available commands",
        [
            "Authentication and common: USER, PASS, QUIT, NOOP, HELP",
            "Directory management: PWD, CWD, CDUP, MKD, RMD",
            "Directory listing and metadata: LIST, NLST, STAT, SIZE, MDTM",
            "Transfer setup: TYPE, MODE, PORT, PASV",
            "File transfer: RETR, STOR, STOU, APPE, ABOR",
            "File management and integrity: DELE, RNFR, RNTO, HASH",
            "Use HELP <command> for detailed syntax and description.",
        ],
    )
