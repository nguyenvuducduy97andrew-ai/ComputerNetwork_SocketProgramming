import struct
# ----Cấu hình dữ liệu----
MAX_PAYLOAD = 1024 # Kích thước khối dữ liệu tối đa đọc từ file (1kb)
HEADER_FORMAT = '!IIHHB' # Cấu trúc header: Seq(4B), Ack(4B), Checksum(2B), Length(2B), Flags(1B)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT) # Tự động tính kích thước header (13 bytes)
BUFFER_SIZE = HEADER_SIZE + MAX_PAYLOAD # Kích thước vùng đệm nhận UDP (1037 bytes)

# ----Cấu hình thời gian và cửa sổ----
TIMEOUT = 0.3 # RTO (Retransmission Timeout) = 0.3s
WINDOW_SIZE = 8 # Kích thước cửa sổ trượt N = 8 packets
DUP_ACK_THRESHOLD = 3 # Ngưỡng 3 Duplicate ACKs để kích hoạt Fast Retransmit

# ----Cờ điều khiển (FLAGS - Bitwise 1 byte)
FLAG_SYN = 0b00000001 # Bit 0: Khởi tạo kết nối RDT
FLAG_ACK = 0b00000010 # Bit 1: Gói tin xác nhận
FLAG_FIN = 0b00000100 # Bit 2: Báo hiệu kết thúc truyền file
FLAG_DATA = 0b00001000 # Bit 3: Gói tin chứa dữ liệu