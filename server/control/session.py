# Lớp quản lý trạng thái của từng Client kết nối đến
class ClientSession:
    def __init__(self):
        self.cwd = '/'          # Current working directory
        self.logged_in = False  # Trạng thái đăng nhập
        self.mode = 'A'         # Transfer mode (A: ASCII, I: Binary)
        self.data_port = None   # Cổng kênh dữ liệu UDP đang cấu hình
