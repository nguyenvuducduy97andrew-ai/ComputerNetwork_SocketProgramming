from enum import Enum
# Mã phản hồi chuẩn RFC 959
class FTPReplyCode(Enum):
    PRELIMINARY_OK = 150
    COMMAND_OK = 200
    LOGIN_SUCCESS = 230
    NEED_PASSWORD = 331
    FILE_UNAVAILABLE = 550
