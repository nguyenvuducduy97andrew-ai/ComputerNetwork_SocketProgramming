import socket
import os
import threading
import time
from .constants import (
    HEADER_SIZE,
    MAX_PAYLOAD,
    BUFFER_SIZE,
    TIMEOUT,
    FLAG_DATA,
    FLAG_ACK,
    FLAG_FIN,
    WINDOW_SIZE,
    DUP_ACK_THRESHOLD,
    FLAG_SYN,
    DATA_MAX_RETRIES,
    FIN_MAX_RETRIES,
    FIN_LINGER_TIMEOUT,
)
from .packet_struct import pack_packet, unpack_packet
from .checksum import verify_checksum
from typing import Any, Callable, Optional



ProgressCallback = Callable[[int, int], None] #Mục đích: callback để báo tiến trình truyền dữ liệu (số byte đã gửi/nhận, tổng số byte)


class RDTTeardownTimeout(TimeoutError):
    """Raised when the peer never confirms the FIN handshake."""


class RDTDataTimeout(TimeoutError):
    """Raised when DATA cannot make progress within the retry limit."""


def _raise_if_cancelled(cancel_event: threading.Event | None) -> None:
    """Stop an RDT operation."""
    if cancel_event is not None and cancel_event.is_set():
        raise InterruptedError("Transfer aborted.")


def _normalize_peer_address(address: tuple[str, int]) -> tuple[str, int]:
    """Normalize an IPv4 hostname so it can be compared with recvfrom()."""
    host, port = address
    try:
        host = socket.gethostbyname(host)
    except OSError:
        pass
    return host, port


def _is_valid_fin_packet(packet: dict, expected_seq: int) -> bool:
    """Validate a payload-free FIN for the expected end-of-stream sequence."""
    return (
        packet["flags"] == FLAG_FIN
        and packet["seq"] == expected_seq
        and packet["length"] == 0
        and packet["payload"] == b""
    )


def _linger_after_fin(
    udp_socket: Any,
    sender_addr: tuple[str, int],
    expected_seq: int,
    ack_fin: bytes,
    cancel_event: threading.Event | None,
) -> None:
    """Acknowledge lại các packet FIN bị mất để tránh việc sender bị kẹt."""
    linger_deadline = time.monotonic() + FIN_LINGER_TIMEOUT

    while True:
        _raise_if_cancelled(cancel_event)
        remaining = linger_deadline - time.monotonic()
        if remaining <= 0:
            return

        udp_socket.settimeout(min(TIMEOUT, remaining))
        try:
            packet_bytes, duplicate_sender = udp_socket.recvfrom(BUFFER_SIZE)
        except socket.timeout:
            continue

        if duplicate_sender != sender_addr:
            continue
        if len(packet_bytes) < HEADER_SIZE or not verify_checksum(packet_bytes):
            continue

        try:
            packet = unpack_packet(packet_bytes)
        except ValueError:
            continue

        if _is_valid_fin_packet(packet, expected_seq):
            udp_socket.sendto(ack_fin, sender_addr)
            linger_deadline = time.monotonic() + FIN_LINGER_TIMEOUT


def reliable_send(
    udp_socket: Any,
    dest_addr: tuple,
    data_or_file_path,
    progress_callback: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
    respond_to_syn: bool = False,
) -> None:
    # API gửi file/dữ liệu tin cậy qua UDP sử dụng cơ chế Fast Retransmit (3 Duplicate ACKs) và thuật toán Sliding Window (Go-Back-N)

    _raise_if_cancelled(cancel_event)
    expected_peer = _normalize_peer_address(dest_addr)

    # Đọc dữ liệu đầu vào
    if isinstance(data_or_file_path, str) and os.path.exists(data_or_file_path):
        with open(data_or_file_path, 'rb') as f:
            raw_data = f.read()
    elif isinstance(data_or_file_path, bytes):
        raw_data = data_or_file_path
    else:
        raw_data = str(data_or_file_path).encode('utf-8')

    total_bytes = len(raw_data)
    if progress_callback is not None:
        progress_callback(0, total_bytes)

    # Chỉ giữ một bản payload trong RAM. Packet được đóng gói theo nhu cầu
    # thay vì tạo thêm danh sách chunks và packets cho toàn bộ file.
    total_packets = max(
        1,
        (total_bytes + MAX_PAYLOAD - 1) // MAX_PAYLOAD,
    )

    def make_data_packet(sequence_number: int) -> bytes:
        start = sequence_number * MAX_PAYLOAD
        payload = raw_data[start:start + MAX_PAYLOAD]
        return pack_packet(
            seq=sequence_number,
            ack=0,
            flags=FLAG_DATA,
            data=payload,
        )

    # Khởi tạo trạng thái cửa sổ trượt (Sliding Window)
    base = 0
    next_seq_num = 0
    dup_ack_count = 0
    data_retry_count = 0
    timer_start = 0.0

    udp_socket.settimeout(0.01)  # Non-blocking polling cho việc nhận ACK liên tục

    while base < total_packets:
        _raise_if_cancelled(cancel_event)
        # Gửi tất cả các gói tin còn nằm trong phạm vi Cửa sổ
        while next_seq_num < base + WINDOW_SIZE and next_seq_num < total_packets:
            _raise_if_cancelled(cancel_event)
            udp_socket.sendto(make_data_packet(next_seq_num), dest_addr)
            if base == next_seq_num:
                timer_start = time.monotonic()  # Bật Timer cho gói tin nhỏ nhất chưa ACK
            next_seq_num += 1

        # Lắng nghe ACK phản hồi từ phía Nhận
        try:
            resp, sender_addr = udp_socket.recvfrom(BUFFER_SIZE)
            if sender_addr == expected_peer and verify_checksum(resp):
                try:
                    unpacked = unpack_packet(resp)
                except ValueError:
                    continue
                if (
                    respond_to_syn
                    and unpacked['flags'] == FLAG_SYN
                    and unpacked['length'] == 0
                    and unpacked['payload'] == b""
                ):
                    syn_ack = pack_packet(
                        seq=0,
                        ack=unpacked['seq'],
                        flags=FLAG_SYN | FLAG_ACK,
                    )
                    udp_socket.sendto(syn_ack, dest_addr)
                    # Client vẫn đang bắt tay nên chưa thể ACK DATA. Cho phiên
                    # truyền một cửa sổ timeout mới để đủ thời gian retry SYN.
                    data_retry_count = 0
                    timer_start = time.monotonic()
                    continue
                if unpacked['flags'] & FLAG_ACK:
                    ack_num = unpacked['ack']

                    if ack_num > base:
                        # Cumulative ACK: Cửa sổ trượt tịnh tiến về phía trước
                        base = ack_num
                        if progress_callback is not None:
                            acknowledged_bytes = min(
                                base * MAX_PAYLOAD,
                                total_bytes,
                            )
                            progress_callback(
                                acknowledged_bytes,
                                total_bytes,
                            )
                        dup_ack_count = 0
                        data_retry_count = 0
                        if base < next_seq_num:
                            timer_start = time.monotonic()  # Reset timer cho gói chưa ACK tiếp theo
                    elif ack_num == base:
                        # Nhận ACK trùng lặp (Duplicate ACK)
                        dup_ack_count += 1
                        if dup_ack_count == DUP_ACK_THRESHOLD:
                            # FAST RETRANSMIT: Gửi lại ngay lập tức gói 'base' bị mất
                            if data_retry_count >= DATA_MAX_RETRIES:
                                raise RDTDataTimeout(
                                    f"DATA sequence {base} was not acknowledged "
                                    f"after {DATA_MAX_RETRIES} retries."
                                )
                            udp_socket.sendto(make_data_packet(base), dest_addr)
                            data_retry_count += 1
                            timer_start = time.monotonic()
                            dup_ack_count = 0
        except socket.timeout:
            _raise_if_cancelled(cancel_event)

        # Kiểm tra Timeout (RTO) -> Truyền lại toàn bộ gói trong cửa sổ hiện tại (Go-Back-N)
        if base < next_seq_num and (time.monotonic() - timer_start) > TIMEOUT:
            if data_retry_count >= DATA_MAX_RETRIES:
                raise RDTDataTimeout(
                    f"DATA sequence {base} was not acknowledged "
                    f"after {DATA_MAX_RETRIES} retries."
                )
            for i in range(base, next_seq_num):
                _raise_if_cancelled(cancel_event)
                udp_socket.sendto(make_data_packet(i), dest_addr)
            data_retry_count += 1
            timer_start = time.monotonic()

    if progress_callback is not None:
        progress_callback(total_bytes, total_bytes)

    # Bắt tay kết thúc truyền dữ liệu (FIN Handshake)
    fin_packet = pack_packet(seq = total_packets, ack = 0, flags = FLAG_FIN)
    for _ in range(FIN_MAX_RETRIES):
        _raise_if_cancelled(cancel_event)
        udp_socket.sendto(fin_packet, dest_addr)
        attempt_deadline = time.monotonic() + TIMEOUT

        while True:
            _raise_if_cancelled(cancel_event)
            remaining = attempt_deadline - time.monotonic()
            if remaining <= 0:
                break

            udp_socket.settimeout(remaining)
            try:
                resp, sender_addr = udp_socket.recvfrom(BUFFER_SIZE)
            except socket.timeout:
                _raise_if_cancelled(cancel_event)
                break

            if sender_addr != expected_peer:
                continue
            if len(resp) < HEADER_SIZE:
                continue
            if verify_checksum(resp):
                try:
                    unpacked = unpack_packet(resp)
                except ValueError:
                    continue
                if (
                    unpacked['flags'] == FLAG_FIN
                    and unpacked['ack'] == total_packets
                    and unpacked['seq'] == 0
                    and unpacked['payload'] == b""
                    and unpacked['length'] == 0
                ):
                    return

    raise RDTTeardownTimeout(
        f"FIN handshake failed after {FIN_MAX_RETRIES} attempts."
    )

def reliable_recv(
    udp_socket: socket.socket,
    save_file_path: Optional[str] = None,
    total_bytes: int | None = None,
    progress_callback: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
    expected_peer: tuple[str, int] | None = None,
    respond_to_syn: bool = False,
) -> bytes:
    # API nhận dữ liệu tin cậy qua UDP, đảm bảo ghép nối dữ liệu đúng thứ tự và loại bỏ gói trùng lặp và phản hồi ACK tích lũy.

    _raise_if_cancelled(cancel_event)
    if expected_peer is not None:
        expected_peer = _normalize_peer_address(expected_peer)

    received_data = bytearray()
    expected_seq = 0
    received_bytes = 0
    receive_timeout_count = 0
    udp_socket.settimeout(TIMEOUT)

    if progress_callback is not None and total_bytes is not None:
        progress_callback(0, total_bytes)

    while True:
        _raise_if_cancelled(cancel_event)
        try:
            packet_bytes, sender_addr = udp_socket.recvfrom(BUFFER_SIZE)

            if expected_peer is not None and sender_addr != expected_peer:
                continue
            
            # Kiểm tra lỗi bit
            if not verify_checksum(packet_bytes):
                continue
                
            try:
                unpacked = unpack_packet(packet_bytes)
            except ValueError:
                continue
            flags = unpacked['flags']
            seq = unpacked['seq']

            if respond_to_syn and flags == FLAG_SYN:
                receive_timeout_count = 0
                # Phản hồi SYN để xác nhận kết nối
                syn_ack_packet = pack_packet(seq = 0, ack = seq, flags = FLAG_SYN | FLAG_ACK)
                udp_socket.sendto(syn_ack_packet, sender_addr)
                continue

            
            # Xử lý gói FIN
            if flags == FLAG_FIN:
                if unpacked["length"] != 0 or unpacked["payload"] != b"":
                    continue  # Gói FIN không hợp lệ

                if seq != expected_seq:
                    # FIN đến sớm: báo lại sequence mà receiver vẫn đang chờ.
                    ack_packet = pack_packet(seq = 0, ack = expected_seq, flags = FLAG_ACK)
                    udp_socket.sendto(ack_packet, sender_addr)
                    continue
                receive_timeout_count = 0
                ack_fin = pack_packet(seq = 0, ack = seq, flags = FLAG_FIN)
                udp_socket.sendto(ack_fin, sender_addr)
                _linger_after_fin(
                    udp_socket,
                    sender_addr,
                    expected_seq,
                    ack_fin,
                    cancel_event,
                )
                break  # Kết thúc sau khi đã cho phép sender gửi lại FIN.
    
            # Xử lý gói DATA
            if flags == FLAG_DATA:
                receive_timeout_count = 0
                if seq == expected_seq:
                    # Nhận đúng gói mong đợi -> Đưa vào bộ đệm và tăng Sequence kỳ vọng
                    received_data.extend(unpacked['payload'])
                    expected_seq += 1
                    received_bytes += len(unpacked['payload'])

                    if progress_callback is not None and total_bytes is not None:
                        progress_callback(
                            min(received_bytes, total_bytes),
                            total_bytes,
                        )
                    
                    # Phản hồi Cumulative ACK (Xác nhận đã nhận an toàn đến expected_seq)
                    ack_packet = pack_packet(seq = 0, ack = expected_seq, flags = FLAG_ACK)
                    udp_socket.sendto(ack_packet, sender_addr)
                else:
                    # Nhận sai thứ tự hoặc lặp -> Gửi lại ACK của gói kỳ vọng gần nhất
                    ack_packet = pack_packet(seq = 0, ack = expected_seq, flags = FLAG_ACK)
                    udp_socket.sendto(ack_packet, sender_addr)

        except socket.timeout:
            _raise_if_cancelled(cancel_event)
            receive_timeout_count += 1
            if receive_timeout_count >= DATA_MAX_RETRIES:
                raise RDTDataTimeout(
                    f"No valid DATA was received after "
                    f"{DATA_MAX_RETRIES} consecutive timeouts."
                )

    _raise_if_cancelled(cancel_event)

    if save_file_path:
        dir_name = os.path.dirname(save_file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(save_file_path, 'wb') as f:
            f.write(received_data)

    if progress_callback is not None and total_bytes is not None:
        progress_callback(total_bytes, total_bytes)

    return bytes(received_data)
