import sys
import os
import socket
import random
import threading
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.rdt_core import reliable_recv, reliable_send
from shared.checksum import compute_file_hash

class LossyUDPSocket:
    # Wrapper cho UDP Socket để giả lập mất gói tin ngẫu nhiên.

    def __init__(self, real_socket: socket.socket, drop_rate: float = 0.20):
        self.sock = real_socket
        self.drop_rate = drop_rate
    
    def sendto(self, data, addr):
        # Tỉ lệ 20% làm mất gói tin
        if random.random() < self.drop_rate:
            return
        self.sock.sendto(data, addr)
    
    def recvfrom(self, bufsize):
        return self.sock.recvfrom(bufsize)
    
    def settimeout(self, t):
        self.sock.settimeout(t)

def run_test():
    print("=== TEST MÔ PHỎNG RDT TRÊN MẠNG LỖI (MẤT 20% GÓI TIN) ===")
    server_addr = ('127.0.0.1', 9998)

    # Tạo file nhị phân mẫu 100kB để test
    test_file_path = "tests/sample_input.bin"
    output_file_path = "tests/sample_output.bin"
    os.makedirs("tests", exist_ok=True)
    
    sample_bytes = os.urandom(100 * 1024)  # 100 KB dữ liệu ngẫu nhiên
    with open(test_file_path, "wb") as f:
        f.write(sample_bytes)
        
    src_hash = compute_file_hash(test_file_path)
    print(f"[+] SHA-256 File gốc:  {src_hash}")

    # Tạo Luồng Server Nhận File
    def server_thread():
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.bind(server_addr)
        reliable_recv(recv_sock, save_file_path=output_file_path)
        recv_sock.close()

    t = threading.Thread(target=server_thread)
    t.start()
    time.sleep(0.1)

    # Phía Gửi chạy qua Lossy Socket (Mất 20% gói tin)
    send_sock_raw = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    lossy_sock = LossyUDPSocket(send_sock_raw, drop_rate=0.20)
    
    start_time = time.time()
    print("[+] Bắt đầu truyền file 100KB qua Sliding Window (GBN) trên mạng lỗi 20%...")
    reliable_send(lossy_sock, server_addr, test_file_path)
    elapsed = time.time() - start_time
    
    t.join()
    send_sock_raw.close()

    # Đánh giá tính toàn vẹn end-to-end bằng SHA-256
    dest_hash = compute_file_hash(output_file_path)
    print(f"[+] SHA-256 File nhận: {dest_hash}")
    print(f"[+] Thời gian truyền:   {elapsed:.2f} giây")

    # Dọn dẹp file test
    if os.path.exists(test_file_path): os.remove(test_file_path)
    if os.path.exists(output_file_path): os.remove(output_file_path)

    assert src_hash == dest_hash, "LỖI: Hash không khớp, dữ liệu bị sai lệch!"
    print("\n KẾT QUẢ EXCELLENT: File truyền thành công 100% nguyên vẹn, Hash trùng khớp dù bị đứt gói 20%!")

if __name__ == '__main__':
    run_test()