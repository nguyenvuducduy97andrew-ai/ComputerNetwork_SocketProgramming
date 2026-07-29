from enum import Enum

# Từ điển status/mã mà server trả về khi liên lạc với client
class FTPReplyCode(Enum):

    #Positive preliminary reply
    DATA_CONNECTION_ALREADY_OPEN = (125, "Data connection already open; transfer starting.")
    PRELIMINARY_OK = (150, "File stable; preparing to open data connection.")

    #Completion reply (positive)
    COMMAND_OK = (200, "Command okay.")
    FILE_STATUS = (213, "File status.")
    HELP_MESSAGE = (214, "Help message.")
    SERVICE_READY = (220, "Service ready for new user.")
    GOODBYE = (221, "Goodbye.")
    TRANSFER_COMPLETE = (226, "Closing data connection. Transfer complete.")
    ENTERING_PASSIVE_MODE = (227, "Entering Passive Mode.")
    LOGIN_SUCCESS = (230, "User logged in successfully.")
    FILE_ACTION_OK = (250, "Requested file action okay, completed.")
    PATH_CREATED = (257, "Pathname created.")
    #Positive intermediate reply
    NEED_PASSWORD = (331, "User name okay, need password.")
    FILE_ACTION_PENDING = (350, "Requested file action pending further information.")

    #Negative transient reply: Những lỗi tạm thời, có thể thành công trong một session khác
    SERVICE_UNAVAILABLE = (421, "Service unavailable.")
    CANNOT_OPEN_DATA_CONNECTION = (425, "Cannot open data connection.")
    TRANSFER_ABORTED = (426, "Connection closed; transfer aborted.")
    FILE_TEMPORARILY_UNAVAILABLE = (450, "File unavailable temporarily.")
    LOCAL_PROCESSING_ERROR = (451, "Requested action aborted: local error in processing.")
    
    #Permanent negative reply: Những lỗi ko thể fix/ko phải do session
    SYNTAX_ERROR = (500, "Syntax error, command not recognized.")
    INVALID_PARAMETER = (501, "Syntax error in parameters or arguments.")
    COMMAND_NOT_IMPLEMENTED = (502, "Command not implemented.")
    BAD_COMMAND_SEQUENCE = (503, "Bad sequence of commands.")
    NOT_LOGGED_IN = (530, "Not logged in.")
    FILE_UNAVAILABLE = (550, "Requested action not taken. File unavailable.")

    def __init__(self, code: int, message: str): #tự truyền self (this) làm một parameter
        self.code = code
        self.message = message

    def format(self, custom_message: str | None = None) -> str:
        if custom_message is not None:
            message = custom_message
        else:
            message = self.message
        result = f"{self.code} {message}\r\n"
        return result

    def format_multiline(self, first_message: str, lines: list[str], last_message: str = "End") -> str:
        body = "".join(f"{line}\r\n" for line in lines)
        return f"{self.code}-{first_message}\r\n{body}{self.code} {last_message}\r\n"
