from enum import Enum

# Từ điển status/mã mà server trả về khi liên lạc với client
class FTPReplyCode(Enum):

    #Positive preliminary reply
    DATA_CONNECTION_ALREADY_OPEN = (125, "Kết nối dữ liệu đã được mở.")
    PRELIMINARY_OK = (150, "File ổn; chuẩn bị mở kết nối dữ liệu.")

    #Completion reply (positive)
    COMMAND_OK = (200, "Lệnh đã được chấp nhận.")
    SERVICE_READY = (220, "Dịch vụ sẵn sàng.")
    GOODBYE = (221, "Tạm biệt.")
    TRANSFER_COMPLETE = (226, "Đang đóng kết nối dữ liệu. Truyền hoàn tất.")
    LOGIN_SUCCESS = (230, "Người dùng đã đăng nhập.")
    FILE_ACTION_OK = (250, "Thao tác với file đã thực hiện thành công.")
    PATH_CREATED = (257, "Đường truyền đã được tạo.")
    #Positive intermediate reply
    NEED_PASSWORD = (331, "Tên người dùng hợp lệ, cần mật khẩu.")
    FILE_ACTION_PENDING = (350, "Yêu cầu thao tác tệp đang chờ thêm thông tin.")

    #Negative transient reply: Những lỗi tạm thời, có thể thành công trong một session khác
    SERVICE_UNAVAILABLE = (421, "Dịch vụ không khả dụng.")
    CANNOT_OPEN_DATA_CONNECTION = (425, "Không thể mở kết nối dữ liệu.")
    TRANSFER_ABORTED = (426, "Kết nối đã đóng; truyền file bị hủy.")
    FILE_TEMPORARILY_UNAVAILABLE = (450, "Tệp được yêu cầu tạm thời không khả dụng.")
    
    #Permanent negative reply: Những lỗi ko thể fix/ko phải do session
    SYNTAX_ERROR = (500, "Lỗi cú pháp, không nhận diện/không hỗ trợ lệnh.")
    INVALID_PARAMETER = (501, "Lỗi cú pháp trong tham số hoặc đối số.")
    COMMAND_NOT_IMPLEMENTED = (502, "Lệnh chưa được cài đặt trong server.")
    NOT_LOGGED_IN = (530, "Chưa đăng nhập.")
    FILE_UNAVAILABLE = (550, "Yêu cầu không được thực hiện. Tệp không khả dụng.")

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
