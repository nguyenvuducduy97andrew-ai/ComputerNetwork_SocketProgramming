# Định nghĩa các hằng số hệ thống
MAX_PAYLOAD = 1024       # Kích thước tối đa của payload UDP
TIMEOUT = 1.0            # Thời gian timeout retransmit (giây)
WINDOW_SIZE = 8          # Kích thước cửa sổ sliding window
HEADER_FORMAT = '!IIHH'  # Định nghĩa format struct: Seq, Ack, Checksum, Flags
