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
    client_address: tuple[str, int]
    server_root: Path 
    username: str | None = None
    authenticated: bool = False
    current_directory: Path = Path(".") 

    transfer_type: str = "I" #A hoặc I (ASCII hoặc Binary)
    transfer_mode: str = "S" # "S" (Stream), "B" (Block), "C" (Compressed)
    data_connection_mode: str | None = None # "ACTIVE" hoặc "PASSIVE"

    current_transfer_command: str | None = None
    control_conn: socket | None = None
    
    active_udp_address: tuple[str, int] | None = None 

    passive_udp_socket: socket | None = None 
    passive_client_address: tuple[str, int] | None = None

    pending_rename_path: Path | None = None 

    transfer_in_progress: bool = False 
    current_transfer_file: Path | None = None
    current_transfer_direction: str | None = None # "UPLOAD" hoặc "DOWNLOAD"
    expected_transfer_size: int = 0 #in byte
    transferred_bytes: int = 0

    connected_at: datetime = field(default_factory=datetime.now)
    last_activity_at: datetime = field(default_factory=datetime.now)

    # Event dùng để báo hủy truyền khi Client gửi ABOR

    transfer_thread: threading.Thread | None = None
    conn_send_lock: threading.Lock = field(default_factory=threading.Lock) #Bảo vệ việc gửi dữ liệu qua socket
    cancel_event: threading.Event = field(default_factory=threading.Event) #Dùng để báo hủy truyền file
    transfer_lock: threading.Lock = field(default_factory=threading.Lock) #Bảo vệ trạng thái truyền file

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
                    final_reply = FTPReplyCode.TRANSFER_ABORTED.format("Abort request accepted.")
                except Exception as exc:
                    final_reply = FTPReplyCode.TRANSFER_ABORTED.format(f"Transfer failed: {exc}")
                finally:
                    self.finish_transfer()

                if self.control_conn is not None:
                    with self.conn_send_lock:
                        try:
                            self.control_conn.sendall(final_reply.encode("utf-8"))
                        except OSError:
                            pass

                with self.transfer_lock:
                    self.transfer_thread = None

            thread = threading.Thread(target=_run, daemon=True)
            self.transfer_thread = thread
            thread.start()





