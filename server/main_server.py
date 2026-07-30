import socket
import threading
from pathlib import Path

from server.control.command_result import iter_command_replies
from server.control.ftp_codes import FTPReplyCode
from server.control.command_handler import handle_command
from server.control.session import ClientSession

# Control thread:
def handle_client(conn: socket.socket, addr: tuple[str, int], server_root: Path) -> None:
    """Per-connection handler: send welcome, receive commands, respond."""
    with conn:
        session: ClientSession | None = None
        try:
            # Send initial service ready message
            conn.sendall(FTPReplyCode.SERVICE_READY.format().encode())

            session = ClientSession(client_address=addr, server_root=server_root)
            session.control_conn = conn

            buffer = bytearray()

            while True:
                data = conn.recv(1024)
                if not data:
                    break
                buffer.extend(data)

                while b"\r\n" in buffer:
                    raw_line, _, remaining = buffer.partition(b"\r\n")
                    buffer = bytearray(remaining)
                    line = raw_line.decode('utf-8', errors='ignore').strip('\r\n')
                    if not line:
                        continue

                    parts = line.split(' ', 1)
                    command = parts[0].upper()
                    args = parts[1] if len(parts) > 1 else None

                    if args:
                        logged_args = "********" if command == "PASS" else args
                        print(f"[{addr[0]}:{addr[1]}] Received command: {command} {logged_args}")
                    else:
                        print(f"[{addr[0]}:{addr[1]}] Received command: {command}")

                    result = handle_command(session, command, args)

                    for response, close_control in iter_command_replies(result):
                        try:
                            with session.conn_send_lock:
                                conn.sendall(response.encode("utf-8"))
                            reply_code = response.split(" ", 1)[0]
                            print(
                                f"[{addr[0]}:{addr[1]}] "
                                f"Sent reply {reply_code}."
                            )
                        except OSError as exc:
                            print(f"[{addr[0]}:{addr[1]}] Error sending response: {exc}")
                            return

                        if close_control:
                            return

        except Exception as exc:
            # On unexpected error, try to close connection gracefully
            print(f"[{addr[0]}:{addr[1]}] Unexpected error occurred: {exc}")
            try:
                conn.sendall(FTPReplyCode.SERVICE_UNAVAILABLE.format().encode())
            except Exception:
                pass
        finally:
            if session is not None:
                session.reset_data_connection()
                print(f"[{addr[0]}:{addr[1]}] Connection closed.")


def run_server(host: str = '0.0.0.0', port: int = 2121) -> None:
    server_root = Path("data").resolve()
    server_root.mkdir(parents=True, exist_ok=True)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print(f"Starting Hybrid FTP Server on {host}:{port}...")
        srv.bind((host, port))
        print(f"Server root directory: {server_root.resolve()}")
        srv.listen(5)
        print("Press Ctrl+C to stop the server.")

        try:
            while True:
                conn, addr = srv.accept()
                print(f"Received connection from {addr[0]}:{addr[1]}")
                thread = threading.Thread(target=handle_client, args=(conn, addr, server_root), daemon=True)
                thread.start()
                print(f"Started thread {thread.name} for {addr[0]}:{addr[1]}")
        except KeyboardInterrupt: #Shutdown server on Ctrl+C
            print("Shutting down server...")


if __name__ == '__main__':
    run_server()
