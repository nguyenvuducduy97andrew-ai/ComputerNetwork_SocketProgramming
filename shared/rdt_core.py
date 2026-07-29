import socket
import os
import time
from .constants import (MAX_PAYLOAD, BUFFER_SIZE, TIMEOUT, FLAG_DATA, FLAG_ACK, FLAG_FIN, WINDOW_SIZE, DUP_ACK_THRESHOLD)
from .packet_struct import pack_packet, unpack_packet
from .checksum import verify_checksum
from typing import Any, Callable, Optional


ProgressCallback = Callable[[int, int], None]


def reliable_send(
    udp_socket: Any,
    dest_addr: tuple,
    data_or_file_path,
    progress_callback: ProgressCallback | None = None,
):
    # API gửi file/dữ liệu tin cậy qua UDP sử dụng cơ chế Fast Retransmit (3 Duplicate ACKs) và thuật toán Sliding Window (Go-Back-N)

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

    # Phân đoạn dữ liệu thành danh sách các gói tin
    chunks = [raw_data[i:i + MAX_PAYLOAD] for i in range(0, len(raw_data), MAX_PAYLOAD)]
    total_packets = len(chunks)

    if total_packets == 0:
        chunks = [b'']
        total_packets = 1

    packets = [pack_packet(seq = i, ack = 0, flags = FLAG_DATA, data = chunks[i]) for i in range(total_packets)]

    # Khởi tạo trạng thái cửa sổ trượt (Sliding Window)
    base = 0
    next_seq_num = 0
    dup_ack_count = 0
    last_ack_received = -1
    timer_start = 0

    udp_socket.settimeout(0.01)  # Non-blocking polling cho việc nhận ACK liên tục

    while base < total_packets:
        # Gửi tất cả các gói tin còn nằm trong phạm vi Cửa sổ
        while next_seq_num < base + WINDOW_SIZE and next_seq_num < total_packets:
            udp_socket.sendto(packets[next_seq_num], dest_addr)
            if base == next_seq_num:
                timer_start = time.time()  # Bật Timer cho gói tin nhỏ nhất chưa ACK
            next_seq_num += 1

        # Lắng nghe ACK phản hồi từ phía Nhận
        try:
            resp, _ = udp_socket.recvfrom(BUFFER_SIZE)
            if verify_checksum(resp):
                unpacked = unpack_packet(resp)
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
                        if base < next_seq_num:
                            timer_start = time.time()  # Reset timer cho gói chưa ACK tiếp theo
                    elif ack_num == base:
                        # Nhận ACK trùng lặp (Duplicate ACK)
                        dup_ack_count += 1
                        if dup_ack_count == DUP_ACK_THRESHOLD:
                            # FAST RETRANSMIT: Gửi lại ngay lập tức gói 'base' bị mất
                            udp_socket.sendto(packets[base], dest_addr)
                            timer_start = time.time()
                            dup_ack_count = 0
        except socket.timeout:
            pass

        # Kiểm tra Timeout (RTO) -> Truyền lại toàn bộ gói trong cửa sổ hiện tại (Go-Back-N)
        if base < next_seq_num and (time.time() - timer_start) > TIMEOUT:
            for i in range(base, next_seq_num):
                udp_socket.sendto(packets[i], dest_addr)
            timer_start = time.time()

    if progress_callback is not None:
        progress_callback(total_bytes, total_bytes)

    # Bắt tay kết thúc truyền dữ liệu (FIN Handshake)
    fin_packet = pack_packet(seq = total_packets, ack = 0, flags = FLAG_FIN)
    udp_socket.settimeout(TIMEOUT)
    while True:
        try:
            udp_socket.sendto(fin_packet, dest_addr)
            resp, _ = udp_socket.recvfrom(BUFFER_SIZE)
            if verify_checksum(resp):
                unpacked = unpack_packet(resp)
                if unpacked['flags'] & FLAG_FIN:
                    break
        except socket.timeout:
            pass

def reliable_recv(
    udp_socket: socket.socket,
    save_file_path: Optional[str] = None,
    total_bytes: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> bytes:
    # API nhận dữ liệu tin cậy qua UDP, đảm bảo ghép nối dữ liệu đúng thứ tự và loại bỏ gói trùng lặp và phản hồi ACK tích lũy.

    received_chunks = {}
    expected_seq = 0
    received_bytes = 0
    udp_socket.settimeout(2.0)

    if progress_callback is not None and total_bytes is not None:
        progress_callback(0, total_bytes)

    while True:
        try:
            packet_bytes, sender_addr = udp_socket.recvfrom(BUFFER_SIZE)
            
            # Kiểm tra lỗi bit
            if not verify_checksum(packet_bytes):
                continue
                
            unpacked = unpack_packet(packet_bytes)
            flags = unpacked['flags']
            seq = unpacked['seq']
            
            # Xử lý gói FIN
            if flags & FLAG_FIN:
                ack_fin = pack_packet(seq = 0, ack = seq, flags = FLAG_FIN)
                udp_socket.sendto(ack_fin, sender_addr)
                break

            # Xử lý gói DATA
            if flags & FLAG_DATA:
                if seq == expected_seq:
                    # Nhận đúng gói mong đợi -> Đưa vào bộ đệm và tăng Sequence kỳ vọng
                    received_chunks[seq] = unpacked['payload']
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
            continue

    # Ráp lại toàn bộ payload theo đúng thứ tự Sequence Number
    full_data = bytearray()
    for i in range(expected_seq):
        if i in received_chunks:
            full_data.extend(received_chunks[i])

    if save_file_path:
        dir_name = os.path.dirname(save_file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(save_file_path, 'wb') as f:
            f.write(full_data)

    if progress_callback is not None and total_bytes is not None:
        progress_callback(total_bytes, total_bytes)

    return bytes(full_data)
