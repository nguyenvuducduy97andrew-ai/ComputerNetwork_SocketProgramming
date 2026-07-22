
from server.control.ftp_codes import FTPReplyCode
from server.control.session import ClientSession
from server.auth.user_db import authenticate


def handle_user(session: ClientSession, args: str | None) -> str:
    if not args:
        return FTPReplyCode.SYNTAX_ERROR.format("Missing username argument.")

    session.username = args
    return FTPReplyCode.NEED_PASSWORD.format()

def handle_pass(session: ClientSession, args: str | None) -> str:
    if not args:
        return FTPReplyCode.SYNTAX_ERROR.format("Missing password argument.")

    if session.username is None:
        return FTPReplyCode.NOT_LOGGED_IN.format("Username must be provided before password.")
    # Check username/password against the user DB
    if authenticate(session.username, args):
        session.authenticated = True
        return FTPReplyCode.LOGIN_SUCCESS.format()
    else:
        return FTPReplyCode.NOT_LOGGED_IN.format("Invalid username or password.")

def handle_quit(session: ClientSession) -> str:
    session.logout()
    return FTPReplyCode.GOODBYE.format("Goodbye.")