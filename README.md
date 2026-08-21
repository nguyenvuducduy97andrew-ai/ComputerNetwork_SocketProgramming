# Hybrid FTP Client–Server (tổng quan cập nhật)

Ứng dụng truyền tệp theo mô hình Client–Server, tách thành hai kênh:

- **Control channel (TCP):** nhận/ghi lệnh FTP-like và trả các mã reply theo chuẩn nội bộ.
- **Data channel (UDP + RDT):** truyền danh sách và nội dung tệp bằng giao thức Reliable Data Transfer tự triển khai.

Hai thành phần chính là `client/` và `server/`; các tiện ích giao thức dùng chung nằm trong `shared/`.

## Yêu cầu

- Python 3.10+
- Không cần thư viện ngoài (dùng standard library).
- Chạy các lệnh từ thư mục gốc của repository.

## Chạy server & client (nhanh)

Chạy từ thư mục gốc dự án (nơi chứa `server/`, `client/`, `data/`):

Máy server:
```powershell
cd 'c:\Users\PC\OneDrive\Máy tính\MMT_Projects_SocketPrograming'
ipconfig
python -m server.main_server
```

Ghi lại `IPv4 Address` của card Wi-Fi đang dùng. Server mặc định lắng nghe TCP trên `0.0.0.0:2121` và sử dụng thư mục `data/server_storage/` làm server root.

Máy client (thay IP ví dụ bằng IPv4 của máy server):
```powershell
cd 'c:\Users\PC\OneDrive\Máy tính\MMT_Projects_SocketPrograming'
python -m client.main_client --host 192.168.1.10 --port 2121
```

Không dùng `localhost` hoặc `127.0.0.1` khi chạy hai máy vì chúng trỏ về chính máy client. Tùy chọn `-u` chỉ làm log hiện ngay khi redirect output, không bắt buộc khi chạy tương tác. Client cung cấp prompt `ftp>` để nhập lệnh. File tải về mặc định lưu tại `data\client_downloads\`.

Tài khoản mặc định đọc từ `server/auth/user.json` (ví dụ có user `admin` với password `123456`).

## Các lệnh chính (tổng quát)

- Xác thực & phiên: `USER`, `PASS`, `QUIT`, `NOOP`, `HELP`
- Thư mục: `PWD`, `CWD`, `CDUP`, `MKD`, `RMD`
- Listing & metadata: `LIST`, `NLST`, `STAT`, `SIZE`, `MDTM`
- Thiết lập truyền: `TYPE`, `MODE`, `PORT`, `PASV`
- Truyền dữ liệu: `RETR`, `STOR`, `STOU`, `APPE`, `ABOR`
- Quản lý tệp: `DELE`, `RNFR`, `RNTO`, `HASH`

Lưu ý: `USER`/`PASS` phải dùng trước khi gọi các lệnh yêu cầu xác thực.

## Data channel: khái quát sử dụng

- `PASV`: server mở UDP socket động và trả `227 ... UDP_PORT=<port>`; client sử dụng `(server_host, port)` làm đích UDP. Passive handshake gửi SYN probe, chờ SYN-ACK và retry tối đa 5 lần nếu probe hoặc SYN-ACK bị mất.
- `PORT <udp-port>`: client bind UDP local và báo port cho server để sử dụng active mode.
- `TYPE I`/`TYPE A` quy định binary hoặc chuẩn hóa newline. `MODE S` truyền stream, `MODE B` đóng khung descriptor–length–data có EOF, và `MODE C` nén bằng zlib.

Trước **mỗi** lệnh `LIST`, `RETR`, `STOR`, `STOU` hoặc `APPE`, bạn phải cấu hình một data channel mới bằng `PASV` hoặc `PORT`. Client đóng data channel sau khi transfer kết thúc.

Ví dụ ngắn (client prompt):
```text
USER admin
PASS 123456
TYPE I
MODE S
PASV
STOR abcabc.txt              # đọc data\client_downloads\abcabc.txt
PASV
RETR abcabc.txt              # lưu data\client_downloads\abcabc.txt
HASH abcabc.txt              # kiểm tra SHA-256 trên server
QUIT
```

## Kiểm chứng (logs, checksum, RDT traces)

- Nếu cần lưu control logs, chạy `New-Item -ItemType Directory -Force logs | Out-Null` trước, rồi thêm `2>&1 | Tee-Object -FilePath logs\server_run.log` hoặc `logs\client_run.log` sau module command tương ứng. Tìm các dòng chứa `PASV|PORT|STOR|RETR` và mã `125|150|226`.
- Checksum: server có lệnh `HASH <file>` trả `SHA-256 <name> <hash>`; ở `TYPE I`, client tự so sánh SHA-256 sau `RETR`, `STOR` và `STOU`. Ở `TYPE A`, client bỏ qua so sánh byte hash vì chuẩn hóa newline có thể thay đổi biểu diễn byte hợp lệ.
- Với `STOU`, server sinh tên dạng UUID và trả `REMOTE_NAME=<tên>`; client dùng đúng tên này khi gọi `HASH`.
- Với `APPE`, client không tự gọi `HASH` vì file local chỉ là phần nối thêm, không tương ứng với toàn bộ file remote. Reply `226` trả `APPENDED_BYTES=<n>` và `FINAL_SIZE=<n>` để xác nhận kết quả.
- RDT/UDP: tiến trình truyền, SYN/ACK/FIN và retransmit được in ra terminal trong khi transfer — chụp màn hình những đoạn này làm minh chứng.

Ví dụ trích log (PowerShell):
```powershell
Select-String -Path logs\client_run.log -Pattern 'PASV|PORT|STOR|RETR|125|150|226' -SimpleMatch
Select-String -Path logs\server_run.log -Pattern 'PASV|PORT|STOR|RETR|125|150|226' -SimpleMatch
```

## Thư mục lưu trữ dữ liệu

- Server root theo code là `data/server_storage/` (được tạo nếu chưa tồn tại).
- Client download mặc định: `data/client_downloads/`.
- Hai vùng lưu trữ được tách riêng để chạy server và client trên cùng máy không làm lẫn file của hai phía.

## Chạy test

Chạy các test unit có sẵn từ thư mục gốc:

```powershell
python tests/test_checksum.py
python tests/test_rdt_lossy.py
python -m unittest discover -s tests -p "test_*.py" -v
```

Hoặc chạy từng test cụ thể với `python -m unittest -v tests.test_active_upload` v.v.

## Điều cần biết (tổng quát, không theo thời gian)

- Data channel là UDP + RDT (Go-Back-N, cumulative ACK, fast retransmit); cửa sổ cố định tại 8 packets. DATA dừng sau tối đa 10 lần retry liên tiếp không có ACK tiến triển; receiver cũng thoát sau 10 RTO liên tiếp không nhận được DATA hợp lệ.
- Mỗi session chỉ có một transfer worker. Ở client, `LIST`/`RETR`/`STOR`/`STOU`/`APPE` chạy nền để prompt vẫn nhận được `ABOR`; các lệnh khác được nhập lại sau khi transfer kết thúc.
- `STOU` dùng UUID để tránh trùng tên khi nhiều upload bắt đầu gần nhau; tên thật trên server luôn được công bố qua trường `REMOTE_NAME`.
- RDT chỉ giữ một bản payload và đóng gói packet theo nhu cầu, nhưng codec vẫn xử lý toàn payload trong RAM để hỗ trợ `TYPE A`/`MODE C`; nên dùng file cỡ vừa khi demo. Hệ thống chưa có congestion control hay dải port cố định cho NAT traversal.
- Khi chạy hai máy qua Wi-Fi/LAN, chọn mạng Private và cho phép Python qua Windows Firewall. Server phải nhận được TCP `2121` và UDP inbound; Active Mode cũng cần UDP inbound trên máy client. Dự án dùng UDP port động nên chỉ mở riêng TCP `2121` là chưa đủ.

Chi tiết thiết kế và luồng hoạt động nằm trong [ARCHITECTURE.md](ARCHITECTURE.md).
