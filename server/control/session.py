# Lớp quản lý trạng thái của từng Client kết nối đến
from dataclasses import dataclass, field
from pathlib import Path
from socket import socket
from server.control.ftp_codes import FTPReplyCode

import threading
from datetime import datetime
from typing import Callable

@dataclass
class ClientSession: 
    client_address: tuple[str, int] #địa chỉ IP và port của Client
    server_root: Path # thư mục gốc của Server, tất cả các đường dẫn file sẽ được resolve từ đây
    username: str | None = None #Tên đăng nhập của Client, None nếu chưa đăng nhập
    authenticated: bool = False # True nếu Client đã đăng nhập thành công, False nếu chưa hoặc đã đăng xuất
    current_directory: Path = Path(".") # Thư mục hiện tại của Client, được resolve từ server_root. Mặc định là "." (thư mục gốc)

    transfer_type: str = "I" #A hoặc I (ASCII hoặc Binary)
    transfer_mode: str = "S" # "S" (Stream), "B" (Block), "C" (Compressed)
    data_connection_mode: str | None = None # "ACTIVE" hoặc "PASSIVE"

    current_transfer_command: str | None = None # "STOR" hoặc "RETR" hoặc None nếu không có truyền file đang diễn ra
    control_conn: socket | None = None # socket kết nối control với Client, None nếu chưa có hoặc đã đóng
    
    active_udp_address: tuple[str, int] | None = None #Địa chỉ IP và port của Client khi sử dụng chế độ truyền dữ liệu chủ động (Active Mode). None nếu không có hoặc đang ở chế độ thụ động (Passive Mode)

    passive_udp_socket: socket | None = None  #Socket UDP mà Server mở ra để lắng nghe kết nối dữ liệu từ Client khi sử dụng chế độ truyền dữ liệu thụ động (Passive Mode). None nếu không có hoặc đang ở chế độ chủ động (Active Mode)
    passive_client_address: tuple[str, int] | None = None # Địa chỉ IP và port của Client khi sử dụng chế độ truyền dữ liệu thụ động (Passive Mode). None nếu không có hoặc đang ở chế độ chủ động (Active Mode)
    current_data_socket: socket | None = None # Socket dữ liệu hiện tại đang được sử dụng để truyền file. Có thể là socket UDP (cho chế độ chủ động) hoặc socket TCP (cho chế độ thụ động). None nếu không có truyền file đang diễn ra.

    pending_rename_path: Path | None = None  #Đường dẫn của file đang chờ đổi tên (RNFR) trước khi nhận lệnh RNTO. None nếu không có lệnh RNFR đang chờ.

    transfer_in_progress: bool = False # True nếu đang có truyền file đang diễn ra (STOR hoặc RETR), False nếu không có truyền file nào đang diễn ra
    current_transfer_file: Path | None = None #Đường dẫn của file đang được truyền (STOR hoặc RETR). None nếu không có truyền file nào đang diễn ra
    current_transfer_direction: str | None = None # "UPLOAD" hoặc "DOWNLOAD"
    expected_transfer_size: int = 0 # Dự kiến kích thước của file đang truyền (STOR hoặc RETR). 0 nếu không có truyền file nào đang diễn ra
    transferred_bytes: int = 0 # Số byte đã truyền thành công trong quá trình truyền file (STOR hoặc RETR). 0 nếu không có truyền file nào đang diễn ra

    connected_at: datetime = field(default_factory=datetime.now) # Thời điểm Client kết nối đến Server. Dùng để tính toán thời gian hoạt động của Client.
    last_activity_at: datetime = field(default_factory=datetime.now) # Thời điểm Client thực hiện lệnh cuối cùng. Dùng để tính toán thời gian không hoạt động của Client.

    # Event dùng để báo hủy truyền khi Client gửi ABOR

    transfer_thread: threading.Thread | None = None # Thread đang thực hiện truyền file (STOR hoặc RETR). None nếu không có truyền file nào đang diễn ra
    conn_send_lock: threading.Lock = field(default_factory=threading.Lock) # Lock để bảo vệ việc gửi dữ liệu qua control_conn, tránh việc nhiều thread cùng gửi dữ liệu đồng thời gây lỗi
    cancel_event: threading.Event = field(default_factory=threading.Event) # Event để báo hủy truyền file khi Client gửi lệnh ABOR. Thread truyền file sẽ kiểm tra event này và dừng truyền nếu event được set.
    transfer_lock: threading.Lock = field(default_factory=threading.Lock) # Lock để bảo vệ việc truy cập và thay đổi trạng thái liên quan đến truyền file (transfer_in_progress, current_transfer_file, current_transfer_direction, expected_transfer_size, transferred_bytes, transfer_thread). Tránh việc nhiều thread cùng thay đổi trạng thái này gây lỗi.
    suppress_transfer_reply: bool = False # True nếu không gửi reply về Client sau khi truyền file xong (dùng khi chuẩn bị đóng control_conn). False nếu gửi reply về Client sau khi truyền file xong.
    cleanup_started: bool = False # True nếu đã bắt đầu dọn dẹp session (cleanup), False nếu chưa. Dùng để tránh việc dọn dẹp nhiều lần gây lỗi.

    def get_absolute_current_directory(self)->Path:
        return (self.server_root.resolve()/self.current_directory).resolve()

    def get_display_current_directory(self) -> str:
        print(f"[ClientSession] Getting display current directory. Current directory: {self.current_directory}")
        if self.current_directory == Path("."):
            return "/"

        return "/" + self.current_directory.as_posix()
    
    def reset_data_connection(self) -> None:
        if self.passive_udp_socket is not None:
            try:
                self.passive_udp_socket.close()
            except OSError:
                pass

        self.data_connection_mode = None
        self.active_udp_address = None
        self.passive_udp_socket = None
        self.passive_client_address = None

    def start_transfer(self, command: str, file_path: Path, direction: str, expected_size: int = 0) -> None:
        """
        Đánh dấu session đang bắt đầu truyền file.
        """
        print(f"[ClientSession] Starting transfer. File: {file_path}, Direction: {direction}, Expected size: {expected_size} bytes")
        self.transfer_in_progress = True
        self.current_transfer_command = command.upper()
        self.current_transfer_file = file_path
        self.current_transfer_direction = direction
        self.expected_transfer_size = expected_size
        self.transferred_bytes = 0
        self.cancel_event.clear()

    def finish_transfer(self) -> None:
        """
        Reset trạng thái sau khi truyền xong or thất bại.
        """
        print(f"[ClientSession] Finishing transfer. File: {self.current_transfer_file}, Direction: {self.current_transfer_direction}")
        self.transfer_in_progress = False
        self.current_transfer_command = None
        self.current_transfer_file = None
        self.current_transfer_direction = None
        self.expected_transfer_size = 0
        self.transferred_bytes = 0
        self.cancel_event.clear()

    def request_abort(self) -> None:
        """
        Client gửi lệnh ABOR -> gọi hàm này.
        """
        print(f"[ClientSession] Requesting abort of transfer. File: {self.current_transfer_file}, Direction: {self.current_transfer_direction}")
        if self.transfer_in_progress:
            self.cancel_event.set()

    def register_data_socket(self, data_socket: socket) -> None:
        """
        Ghi nhận socket dữ liệu hiện tại đang được sử dụng để truyền file.
        """
        with self.transfer_lock:
            if self.cleanup_started:
                raise InterruptedError("Session is closing.")
            self.current_data_socket = data_socket

    def unregister_data_socket(self, data_socket: socket) -> None:
        """
        Xóa socket dữ liệu hiện tại nếu nó trùng với socket được truyền vào.
        """
        with self.transfer_lock:
            if self.current_data_socket is data_socket:
                self.current_data_socket = None

    def close_current_data_socket(self) -> None:
        """
        Đóng socket dữ liệu hiện tại nếu có.
        """
        with self.transfer_lock:
            data_socket = self.current_data_socket
            self.current_data_socket = None

        if data_socket is not None:
            try:
                data_socket.close()
            except OSError:
                pass

    def prepare_control_close(self) -> None:
        """
        Chuẩn bị đóng control connection. Gọi trước khi đóng control_conn.
        """
        with self.conn_send_lock:
            self.suppress_transfer_reply = True

        self.request_abort()
        self.close_current_data_socket()

    def send_transfer_reply(self, reply: str) -> bool:
        """
        Gửi reply về Client sau khi truyền file xong. Trả về True nếu gửi
        thành công, False nếu không gửi được (ví dụ control_conn đã đóng).
        """
        with self.conn_send_lock:
            if self.suppress_transfer_reply or self.control_conn is None:
                return False

            try:
                self.control_conn.sendall(reply.encode("utf-8"))
                return True
            except OSError:
                return False

    def reset_rename_state(self) -> None:
        """
        Xóa trạng thái RNFR đang chờ RNTO.
        """
        print(f"[ClientSession] Resetting rename state.")
        self.pending_rename_path = None

    def record_activity(self) -> None:
        self.last_activity_at = datetime.now()

    def logout(self) -> None:
        """
        Client log out -> Reset trạng thái đăng nhập của Client.
        """
        print(f"[ClientSession] Logging out user: {self.username!r}")
        self.username = None
        self.authenticated = False
        self.reset_rename_state()
        self.reset_data_connection()

    def cleanup(self, *, wait_timeout: float = 2.5) -> None:
        """Hàm dọn dẹp session"""
        with self.transfer_lock:
            if self.cleanup_started:
                return
            self.cleanup_started = True
            transfer_thread = self.transfer_thread

        self.prepare_control_close()
        self.reset_data_connection()

        if (
            transfer_thread is not None
            and transfer_thread is not threading.current_thread()
            and transfer_thread.is_alive()
        ):
            transfer_thread.join(wait_timeout)

        self.username = None
        self.authenticated = False
        self.reset_rename_state()

        with self.conn_send_lock:
            self.control_conn = None

        if transfer_thread is None or not transfer_thread.is_alive():
            if self.transfer_in_progress:
                self.finish_transfer()
            with self.transfer_lock:
                self.transfer_thread = None

    def run_transfer(self, worker_fn: Callable[[], str]) -> None:
        """
        worker_fn: không tham số, thực hiện transfer, trả về reply string cuối
        (vd '226 ...'), hoặc raise để báo lỗi. Chạy trong thread riêng.
        """
        with self.transfer_lock:
            if self.transfer_thread is not None and self.transfer_thread.is_alive():
                raise RuntimeError("A transfer is already in progress for this session.")

            def _run() -> None:
                try:
                    final_reply = worker_fn()
                except InterruptedError:
                    final_reply = FTPReplyCode.TRANSFER_ABORTED.format("Transfer aborted.")
                except Exception as exc:
                    final_reply = FTPReplyCode.TRANSFER_ABORTED.format(f"Transfer failed: {exc}")
                finally:
                    self.finish_transfer()

                self.send_transfer_reply(final_reply)

                with self.transfer_lock:
                    self.transfer_thread = None

            thread = threading.Thread(target=_run, daemon=True)
            self.transfer_thread = thread
            thread.start()





