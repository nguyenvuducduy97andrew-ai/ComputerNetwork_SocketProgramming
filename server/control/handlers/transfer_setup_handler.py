import socket

from server.control.ftp_codes import FTPReplyCode
from server.control.session import ClientSession

# Xử lý các lệnh liên quan đến thiết lập truyền file: TYPE, MODE
#Type: Type là lệnh để thiết lập loại truyền dữ liệu (ASCII hoặc Binary)
#Mode: Mode là lệnh để thiết lập chế độ truyền dữ liệu (Stream, Block, Compressed)
#PORT: PORT là lệnh để thiết lập cổng dữ liệu cho chế độ truyền dữ liệu chủ động (Active Mode)
#PASV: PASV là lệnh để thiết lập chế độ truyền dữ liệu thụ động (Passive Mode)



def handle_type(session: ClientSession, args: str | None) -> str:
    print(f"[transfer_setup_handler] Handling TYPE command with argument: {args!r}")
    if not args:
        return FTPReplyCode.INVALID_PARAMETER.format("Missing type argument.")

    if args.upper() not in ["A", "I"]:
        return FTPReplyCode.INVALID_PARAMETER.format("Invalid type argument. Use 'A' for ASCII or 'I' for Binary.")

    print(f"[transfer_setup_handler] Setting transfer type to: {args.upper()}")
    session.transfer_type = args.upper()

    return FTPReplyCode.COMMAND_OK.format(f"Transfer type set to {session.transfer_type}.")




def handle_mode(session: ClientSession, args: str | None) -> str:
    print(f"[transfer_setup_handler] Handling MODE command with argument: {args!r}")
    if not args:
        return FTPReplyCode.INVALID_PARAMETER.format("Missing mode argument.")

    if args.upper() not in ["S", "B", "C"]:
        return FTPReplyCode.INVALID_PARAMETER.format("Invalid mode argument. Use 'S' for Stream, 'B' for Block, or 'C' for Compressed.")

    print(f"[transfer_setup_handler] Setting transfer mode to: {args.upper()}")
    session.transfer_mode = args.upper()

    return FTPReplyCode.COMMAND_OK.format(f"Transfer mode set to {session.transfer_mode}.")




def handle_port(session: ClientSession, args: str | None) -> str:
    print(f"[transfer_setup_handler] Handling PORT command with argument: {args!r}")

    if not args:
        return FTPReplyCode.INVALID_PARAMETER.format("Missing port argument.")

    try:
        port = int(args)
        if port <= 0 or port > 65535:
            return FTPReplyCode.INVALID_PARAMETER.format("Invalid port number. Must be between 1 and 65535.")
    except ValueError:
        return FTPReplyCode.INVALID_PARAMETER.format("Port argument must be a valid integer.")

    print(f"[transfer_setup_handler] Setting data connection mode to ACTIVE on port: {port}")
    session.reset_data_connection()
    session.active_udp_address = (session.client_address[0], port)
    session.data_connection_mode = "ACTIVE"

    return FTPReplyCode.COMMAND_OK.format(f"Data connection mode has been set to ACTIVE on port {port}.")




def handle_pasv(session: ClientSession) -> str:
    print(f"[transfer_setup_handler] Handling PASV command.")

    session.reset_data_connection()
    passive_socket: socket.socket | None = None


    try:

        passive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        passive_socket.bind(('', 0))  # Bind to any available port
        passive_port = passive_socket.getsockname()[1]
        # Đặt một địa chỉ cho passive_socket trước khi thay đổi thông tin session nhằm tránh rò rỉ thông tin nếu có lỗi xảy ra
        session.passive_udp_socket = passive_socket
        session.passive_client_address = None
        session.data_connection_mode = "PASSIVE"
    except OSError as exc:
        if passive_socket is not None:
            passive_socket.close()
        print(f"[transfer_setup_handler] Failed to enter passive mode: {exc}")
        return FTPReplyCode.CANNOT_OPEN_DATA_CONNECTION.format("Failed to enter passive mode.")
    return FTPReplyCode.ENTERING_PASSIVE_MODE.format(
        f"Data connection mode set to PASSIVE. UDP_PORT={passive_port}"
    )
