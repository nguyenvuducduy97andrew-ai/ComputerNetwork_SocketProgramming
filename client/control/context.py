import socket
from dataclasses import dataclass


@dataclass
class ClientContext:
    server_host: str

    username: str | None = None
    authenticated: bool = False

    transfer_type: str = "I"
    transfer_mode: str = "S"

    data_connection_mode: str | None = None
    data_socket: socket.socket | None = None
    data_peer_address: tuple[str, int] | None = None

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
