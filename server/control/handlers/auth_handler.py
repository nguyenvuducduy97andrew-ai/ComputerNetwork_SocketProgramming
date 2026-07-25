
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

    if not user_exists(username):
        session.username = None
        session.authenticated = False
        return FTPReplyCode.INVALID_PARAMETER.format("Invalid username.")

    session.username = username
    session.authenticated = False
    print(f"[auth_handler] Username {username!r} exists. Awaiting password.")

    return FTPReplyCode.NEED_PASSWORD.format()

def handle_pass(
    session: ClientSession,
    password: str | None
) -> str:
    print(f"[auth_handler] Handling PASS command for username: {session.username!r}")
    if session.username is None:
        return FTPReplyCode.INVALID_PARAMETER.format("Missing username argument.")
    print(f"[auth_handler] Authenticating user {session.username!r} with provided password: {password!r}")
    if password is None or password == "":
        return FTPReplyCode.INVALID_PARAMETER.format("Missing password argument.")

    success= authenticate(session.username, password)

    if not success:
        session.authenticated = False
        return FTPReplyCode.INVALID_PARAMETER.format("Invalid password.")

    session.authenticated = True
    return FTPReplyCode.LOGIN_SUCCESS.format()

def handle_quit(session: ClientSession) -> str:
    print(f"Client {session.client_address[0]}:{session.client_address[1]} disconnected.")
    session.logout()
    return FTPReplyCode.GOODBYE.format("Goodbye.")