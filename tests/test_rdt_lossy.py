import os
import random
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.checksum import compute_file_hash
from shared.rdt_core import reliable_recv, reliable_send
from tests.reporting import print_test_result, print_test_step, print_test_suite


class LossyUDPSocket:
    """Bọc UDP socket để giả lập mất gói tin ngẫu nhiên."""

    def __init__(self, real_socket: socket.socket, drop_rate: float = 0.20):
        self.sock = real_socket
        self.drop_rate = drop_rate
    
    def sendto(self, data, addr):
        if random.random() < self.drop_rate:
            return
        self.sock.sendto(data, addr)
    
    def recvfrom(self, bufsize):
        return self.sock.recvfrom(bufsize)
    
    def settimeout(self, timeout):
        self.sock.settimeout(timeout)


def run_test() -> None:
    print_test_suite("RDT TRÊN MẠNG MẤT 20% GÓI TIN")
    server_address = ("127.0.0.1", 9998)

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / "du_lieu_gui.bin"
        output_path = Path(temp_dir) / "du_lieu_nhan.bin"
        input_path.write_bytes(os.urandom(100 * 1024))

        source_hash = compute_file_hash(input_path)
        print_test_step(f"SHA-256 file nguồn: {source_hash}")

        def receive_on_server() -> None:
            receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                receive_socket.bind(server_address)
                reliable_recv(receive_socket, save_file_path=output_path)
            finally:
                receive_socket.close()

        receive_thread = threading.Thread(target=receive_on_server)
        receive_thread.start()
        time.sleep(0.1)

        raw_send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        lossy_socket = LossyUDPSocket(raw_send_socket, drop_rate=0.20)

        print_test_step(
            "Truyền file 100 KB bằng Sliding Window trên mạng mất gói"
        )
        start_time = time.monotonic()
        try:
            reliable_send(lossy_socket, server_address, input_path)
        finally:
            raw_send_socket.close()
        elapsed = time.monotonic() - start_time

        receive_thread.join()
        destination_hash = compute_file_hash(output_path)
        print_test_step(f"SHA-256 file nhận: {destination_hash}")
        print_test_step(f"Thời gian truyền: {elapsed:.2f} giây")

        assert source_hash == destination_hash, (
            "Hash không khớp, dữ liệu nhận đã bị sai lệch."
        )
        print_test_result(
            "File được truyền nguyên vẹn dù mất ngẫu nhiên 20% gói tin"
        )


if __name__ == "__main__":
    run_test()
