import socket
import threading
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class ClientContext:
    server_host: str
    show_prompt_on_transfer_end: bool = False

    username: str | None = None
    authenticated: bool = False

    transfer_type: str = "I"
    transfer_mode: str = "S"

    data_connection_mode: str | None = None
    data_socket: socket.socket | None = None
    data_peer_address: tuple[str, int] | None = None

    transfer_thread: threading.Thread | None = field(default=None, init=False, repr=False)
    transfer_cancel_event: threading.Event = field(default_factory=threading.Event, init=False, repr=False)
    transfer_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    transfer_phase: str | None = field(default=None, init=False)
    abort_requested: bool = field(default=False, init=False)

    def ensure_data_socket(self, local_port: int = 0) -> socket.socket:
        if self.data_socket is None:
            data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                data_socket.bind(("0.0.0.0", local_port))
            except OSError:
                data_socket.close()
                raise

            self.data_socket = data_socket

        return self.data_socket

    def reset_data_connection(self) -> None:
        if self.data_socket is not None:
            try:
                self.data_socket.close()
            except OSError:
                pass

        self.data_socket = None
        self.data_peer_address = None
        self.data_connection_mode = None

    @property
    def transfer_in_progress(self) -> bool:
        with self.transfer_lock:
            return self.transfer_phase is not None

    def start_transfer(self, worker_fn: Callable[[], None]) -> None:
        """Chạy data transfer ở nền để CLI vẫn có thể nhận lệnh ABOR."""
        with self.transfer_lock:
            if self.transfer_phase is not None:
                raise RuntimeError("A client transfer is already in progress.")
            self.transfer_cancel_event.clear()
            self.abort_requested = False
            self.transfer_phase = "DATA"

            def _run() -> None:
                try:
                    worker_fn()
                except Exception as error:
                    print(f"Transfer failed unexpectedly: {error}")
                finally:
                    self.reset_data_connection()
                    with self.transfer_lock:
                        self.transfer_phase = None
                        self.abort_requested = False
                        self.transfer_cancel_event.clear()
                        self.transfer_thread = None
                    if self.show_prompt_on_transfer_end:
                        # Background output có thể ghi đè prompt mà input() đã
                        # in trước đó; hiển thị lại khi chạy CLI tương tác.
                        print("\nftp> ", end="", flush=True)

            thread = threading.Thread(target=_run, daemon=True)
            self.transfer_thread = thread
            thread.start()

    def request_transfer_abort(self) -> str:
        """Đánh dấu ABOR và trả về trạng thái để caller quyết định gửi lệnh."""
        with self.transfer_lock:
            if self.transfer_phase is None:
                return "IDLE"
            if self.transfer_phase == "FINALIZING":
                return "FINALIZING"
            if self.abort_requested:
                return "PENDING"
            self.abort_requested = True
            self.transfer_cancel_event.set()
            return "REQUESTED"

    def mark_transfer_finalizing(self) -> bool:
        """Không nhận ABOR mới khi worker đã bắt đầu đọc final reply."""
        with self.transfer_lock:
            self.transfer_phase = "FINALIZING"
            return self.abort_requested
