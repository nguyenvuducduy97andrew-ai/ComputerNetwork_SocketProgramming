import struct
from .constants import HEADER_FORMAT, HEADER_SIZE
from .checksum import compute_checksum

def pack_packet(seq: int, ack: int, flags: int, data: bytes = b'') -> bytes:
    # Đóng gói Header và Payload thành mảng byte hoàn chỉnh.
    # Tự động tính toán Checksum chính xác đính kèm vào Header.

    data_len = len(data)
    dummy_header = struct.pack(HEADER_FORMAT, seq, ack, 0, data_len, flags)
    chksum = compute_checksum(dummy_header + data)
    real_header = struct.pack(HEADER_FORMAT, seq, ack, chksum, data_len, flags)

    return real_header + data

def unpack_packet(packet_bytes: bytes) -> dict:
    # Rã mảng Byte nhận được từ Socket thành Dictionary có các trường Header và Payload riêng biệt.
    
    if len(packet_bytes) < HEADER_SIZE:
        raise ValueError("Gói tin nhận được có kích thước nhỏ hơn kích thước Header chuẩn!")

    header_bytes = packet_bytes[:HEADER_SIZE]
    payload = packet_bytes[HEADER_SIZE:]

    seq, ack, checksum, length, flags = struct.unpack(HEADER_FORMAT, header_bytes)

    return {
        'seq': seq,
        'ack': ack,
        'checksum': checksum,
        'length': length,
        'flags': flags,
        'payload': payload,
        'raw_header': header_bytes
    }