"""Client-side handlers for navigation commands."""


from shared.constants import FLAG_SYN
from shared.packet_struct import pack_packet
from shared.rdt_core import reliable_recv

from client.control.client_control import ControlConnection, parse_reply
from client.control.context import ClientContext
from client.control.handlers.common import send_and_print


def handle_pwd(control: ControlConnection) -> bool:
    send_and_print(control, "PWD")
    return True


def handle_cwd(control: ControlConnection, args: str | None) -> bool:
    path = args.strip() if args else ""
    if not path:
        print("Missing destination directory for CWD command.")
        return True

    send_and_print(control, f"CWD {path}")
    return True


def handle_cdup(control: ControlConnection) -> bool:
    send_and_print(control, "CDUP")
    return True

def handle_mkd(control: ControlConnection, args: str | None) -> bool:
    directory_name = args.strip() if args else ""
    if not directory_name:
        print("Missing directory name for MKD command.")
        return True

    send_and_print(control, f"MKD {directory_name}")
    return True

def handle_rmd(control: ControlConnection, args: str | None) -> bool:
    directory_name = args.strip() if args else ""
    if not directory_name:
        print("Missing directory name for RMD command.")
        return True

    send_and_print(control, f"RMD {directory_name}")
    return True

def handle_list(control: ControlConnection, session: ClientContext, args: str | None) -> bool:
    path = args.strip() if args else ""

    if session.data_connection_mode not in {"ACTIVE", "PASSIVE"}:
        print("Configure PORT or PASV before LIST.")
        return True

    if session.data_connection_mode == "PASSIVE" and session.data_peer_address is None:
        print("Configure PASV before LIST.")
        return True

    data_socket = session.ensure_data_socket()
    command = f"LIST {path}" if path else "LIST"
    control.send_command(command)

    preliminary = control.read_reply_line()
    print(preliminary)
    code, _ = parse_reply(preliminary)

    if code not in {125, 150}:
        return True

    if session.data_connection_mode == "PASSIVE":
        probe_packet = pack_packet(seq=0, ack=0, flags=FLAG_SYN)
        data_socket.sendto(probe_packet, session.data_peer_address)

    listing_data = reliable_recv(data_socket)
    listing = listing_data.decode("utf-8", errors="replace")

    if listing:
        print(listing)
    else:
        print("(empty directory)")

    response = control.read_reply_line()
    print(response)
    return True

def handle_nlst(control: ControlConnection, args: str | None) -> bool:
    path = args.strip() if args else ""
    command = f"NLST {path}" if path else "NLST"
    send_and_print(control, command)
    return True


def handle_stat(control: ControlConnection, args: str | None) -> bool:
    path = args.strip() if args else ""
    command = f"STAT {path}" if path else "STAT"
    send_and_print(control, command)
    return True


def handle_size(control: ControlConnection, args: str | None) -> bool:
    path = args.strip() if args else ""
    if not path:
        print("Missing filename for SIZE command.")
        return True

    send_and_print(control, f"SIZE {path}")
    return True


def handle_mdtm(control: ControlConnection, args: str | None) -> bool:
    path = args.strip() if args else ""
    if not path:
        print("Missing filename for MDTM command.")
        return True

    send_and_print(control, f"MDTM {path}")
    return True
