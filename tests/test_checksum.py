import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.checksum import verify_checksum
from shared.constants import FLAG_DATA
from shared.packet_struct import pack_packet, unpack_packet
from tests.reporting import print_test_result, print_test_step, print_test_suite


def test_packet_integrity() -> None:
    print_test_suite("CHECKSUM VÀ CẤU TRÚC GÓI TIN")
    payload = b"Testing RDT Engine Payload 12345"

    print_test_step("Đóng gói dữ liệu mẫu")
    packet = pack_packet(seq=1, ack=0, flags=FLAG_DATA, data=payload)
    print_test_result(f"Tạo gói tin {len(packet)} byte thành công")

    print_test_step("Kiểm tra checksum của gói tin nguyên vẹn")
    assert verify_checksum(packet), "Gói tin nguyên vẹn bị đánh dấu là hỏng."
    print_test_result("Checksum xác nhận gói tin nguyên vẹn")

    print_test_step("Giả lập lỗi bit trên đường truyền")
    corrupted_packet = bytearray(packet)
    corrupted_packet[-1] ^= 0xFF
    assert not verify_checksum(
        bytes(corrupted_packet)
    ), "Không phát hiện được dữ liệu bị hỏng."
    print_test_result("Checksum phát hiện gói tin bị thay đổi")

    print_test_step("Giải mã header và payload")
    unpacked = unpack_packet(packet)
    assert unpacked["seq"] == 1, "Sequence number sau giải mã không chính xác."
    assert unpacked["payload"] == payload, "Payload sau giải mã không chính xác."
    print_test_result("Header và payload được khôi phục chính xác")


if __name__ == "__main__":
    test_packet_integrity()
