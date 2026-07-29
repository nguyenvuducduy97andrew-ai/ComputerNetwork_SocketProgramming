"""TCP client helpers for the Hybrid FTP control channel."""

import socket


class ControlConnection:
    """Manage one persistent TCP control connection."""

    def __init__(self, tcp_socket: socket.socket):
        self.sock = tcp_socket
        self.buffer = bytearray()

    def send_command(self, command: str) -> None:
        """Send one CRLF-terminated command to the server."""
        line = command.rstrip("\r\n") + "\r\n"
        self.sock.sendall(line.encode("utf-8"))

    def read_reply_line(self) -> str:
        """
        Read exactly one CRLF-terminated reply line.

        Any bytes after the first CRLF are retained in the persistent buffer
        for the next call.
        """
        while b"\r\n" not in self.buffer:
            chunk = self.sock.recv(1024)

            if not chunk:
                raise ConnectionError("Server closed the control connection.")

            self.buffer.extend(chunk)

        raw_line, _, remaining = self.buffer.partition(b"\r\n")
        self.buffer = bytearray(remaining)

        return raw_line.decode(
            "utf-8",
            errors="replace"
        )

    def receive_server_greeting(self) -> str:
        """Read the initial service-ready reply."""
        return self.read_reply_line()

    def send_simple_command(self, command: str) -> str:
        """Send a command that is expected to return one reply."""
        self.send_command(command)
        return self.read_reply_line()

    def send_command_and_receive_multiline_response(self, command: str) -> list[str]:
        """Send a command and read a multi-line response."""
        self.send_command(command)
        first_line = self.read_reply_line()
        lines = [first_line]

        if len(first_line) < 4 or not first_line[:3].isdigit() or first_line[3] != "-":
            return lines

        terminator = f"{first_line[:3]} "

        while not lines[-1].startswith(terminator):
            lines.append(self.read_reply_line())

        return lines


def parse_reply(response: str) -> tuple[int | None, str]:
    """Split an FTP-style reply into numeric code and message."""
    if not response:
        return None, ""

    parts = response.split(" ", 1)

    if not parts[0].isdigit():
        return None, response

    code = int(parts[0])
    message = parts[1] if len(parts) > 1 else ""

    return code, message


def parse_ftp_response(response: str) -> tuple[int | None, str]:
    """Backward-compatible alias for older client code."""
    return parse_reply(response)
