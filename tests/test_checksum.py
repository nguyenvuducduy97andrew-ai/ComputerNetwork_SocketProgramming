# tests/test_checksum.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.constants import FLAG_DATA
from shared.packet_struct import pack_packet, unpack_packet
from shared.checksum import verify_checksum

def test_packet_integrity():
    print("--- BẮT ĐẦU TEST CHECKSUM VÀ PACKET STRUCT ---")
    payload = b"Testing RDT Engine Payload 12345"
    
    # 1. Đóng gói
    packet = pack_packet(seq=1, ack=0, flags=FLAG_DATA, data=payload)
    print(f"[+] Tạo gói tin ({len(packet)} bytes) thành công.")
    
    # 2. Kiểm tra tính đúng đắn khi dữ liệu không đổi
    assert verify_checksum(packet) == True, "Lỗi: Gói tin chuẩn bị đánh dấu là hỏng!"
    print("[+] Kiểm tra gói tin nguyên vẹn: CHUẨN (PASS)")
    
    # 3. Giả lập biến đổi Bit trên mạng
    corrupted_packet = bytearray(packet)
    corrupted_packet[-1] ^= 0xFF  # Làm nhiễu byte cuối
    
    assert verify_checksum(bytes(corrupted_packet)) == False, "Lỗi: Không phát hiện được dữ liệu bị hỏng!"
    print("[+] Giả lập gói tin hỏng bit: PHÁT HIỆN LỖI THÀNH CÔNG (PASS)")
    
    # 4. Rã gói tin kiểm tra dữ liệu
    unpacked = unpack_packet(packet)
    assert unpacked['seq'] == 1
    assert unpacked['payload'] == payload
    print("[+] Rã dữ liệu Header và Payload: CHUẨN (PASS)")

if __name__ == '__main__':
    test_packet_integrity()