import hashlib

def compute_checksum(data_bytes: bytes) -> int:
    # Thuật toán Internet Checksum 16-bit (cộng bù 1 tất cả các cụm 16-bit).
    if len(data_bytes) % 2 == 1:
        data_bytes += b'\x00' # Thêm byte 0 nếu dữ liệu có độ dài lẻ để đảm bảo tính toán checksum chính xác.
    
    total_sum = 0
    for i in range(0, len(data_bytes), 2):
        word = (data_bytes[i]<<8) + data_bytes[i+1]
        total_sum += word

        while (total_sum>>16)>0:
            total_sum = (total_sum & 0xFFFF) + (total_sum >> 16)
    return (~total_sum) & 0xFFFF

def verify_checksum(packet_bytes: bytes) -> bool:
    # Kiểm tra xem toàn bộ gói tin (đã đính kèm checksum) có bị hỏng bit hay không.
    # Trả về True nếu dữ liệu hợp lệ (tổng checksum = 0), ngược lại False;
    return compute_checksum(packet_bytes) == 0

def compute_file_hash(file_path: str) -> str:
    # Tính mã băm SHA_256 của tệp tin vật lý (đọc theo từng khối 4KB để tránh tràn RAM).
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception:
        return ""