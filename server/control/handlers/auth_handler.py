
from server.control.command_result import CommandReplies, CommandReply
from server.control.ftp_codes import FTPReplyCode
from server.control.session import ClientSession
from server.auth.user_db import authenticate, user_exists


def handle_user(
    session: ClientSession,
    username: str | None
) -> str:
    print(f"[auth_handler] Handling USER command for username: {username!r}")
    if username is None or username.strip() == "":
        return FTPReplyCode.INVALID_PARAMETER.format("Missing username argument.")

    username = username.strip()
    session.username = None
    session.authenticated = False
    session.reset_rename_state()
    session.reset_data_connection()

    if not user_exists(username):
        return FTPReplyCode.NOT_LOGGED_IN.format("Invalid username.")

    session.username = username
    print(f"[auth_handler] Username {username!r} exists. Awaiting password.")

    return FTPReplyCode.NEED_PASSWORD.format()

def handle_pass(
    session: ClientSession,
    password: str | None
) -> str:
    print(f"[auth_handler] Handling PASS command for username: {session.username!r}")
    if session.username is None:
        return FTPReplyCode.BAD_COMMAND_SEQUENCE.format("Send USER before PASS.")

    if password is None or password == "":
        return FTPReplyCode.INVALID_PARAMETER.format("Missing password argument.")

    success= authenticate(session.username, password)

    if not success:
        session.authenticated = False
        return FTPReplyCode.NOT_LOGGED_IN.format("Authentication failed.")

    session.authenticated = True
    return FTPReplyCode.LOGIN_SUCCESS.format()

def handle_quit(session: ClientSession) -> CommandReplies:
    session.prepare_control_close()
    session.logout()
    yield CommandReply(
        FTPReplyCode.GOODBYE,
        "Goodbye.",
        close_control=True,
    )
