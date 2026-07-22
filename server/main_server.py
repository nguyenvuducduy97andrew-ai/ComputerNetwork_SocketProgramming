import socket
import threading
from pathlib import Path

from server.control.ftp_codes import FTPReplyCode
from server.control.command_handler import handle_command
from server.control.session import ClientSession


def handle_client(conn: socket.socket, addr: tuple[str, int], server_root: Path) -> None:
    """Per-connection handler: send welcome, receive commands, respond."""
    with conn:
        try:
            # Send initial service ready message
            conn.sendall(FTPReplyCode.SERVICE_READY.format().encode())

            session = ClientSession(client_address=addr, server_root=server_root)

            while True:
                data = conn.recv(1024)
                if not data:
                    break

                line = data.decode('utf-8', errors='ignore').strip('\r\n')
                if not line:
                    continue

                parts = line.split(' ', 1)
                command = parts[0].upper()
                args = parts[1] if len(parts) > 1 else None

                response = handle_command(session, command, args)
                try:
                    conn.sendall(response.encode())
                except OSError:
                    break

                if command == 'QUIT':
                    break

        except Exception:
            # On unexpected error, try to close connection gracefully
            try:
                conn.sendall(FTPReplyCode.SERVICE_UNAVAILABLE.format().encode())
            except Exception:
                pass


def run_server(host: str = '0.0.0.0', port: int = 2121) -> None:
    server_root = Path('data/server_storage')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, port))
        srv.listen(5)
        print(f'Server FTP listening on {host}:{port}...')

        try:
            while True:
                conn, addr = srv.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr, server_root), daemon=True)
                thread.start()
        except KeyboardInterrupt:
            print('\nShutting down server...')


if __name__ == '__main__':
    run_server()
