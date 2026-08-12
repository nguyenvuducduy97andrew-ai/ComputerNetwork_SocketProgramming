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

Terminal 1 (server):
```powershell
cd 'c:\Users\PC\OneDrive\Máy tính\MMT_Projects_SocketPrograming'
python server\main_server.py 2>&1 | Tee-Object -FilePath logs\server_run.log
```

Server mặc định lắng nghe TCP trên `0.0.0.0:2121` và sử dụng thư mục `data/` làm server root (nếu không tồn tại, server sẽ tạo `data/`).

Terminal 2 (client):
```powershell
cd 'c:\Users\PC\OneDrive\Máy tính\MMT_Projects_SocketPrograming'
python client\main_client.py --host localhost --port 2121 2>&1 | Tee-Object -FilePath logs\client_run.log
```

Client cung cấp prompt `ftp>` để nhập lệnh. File tải về mặc định lưu tại `data\client_downloads\`.

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

- `PASV`: server mở UDP socket động và trả `227 ... UDP_PORT=<port>`; client sử dụng `(server_host, port)` làm đích UDP trong passive mode.
- `PORT <udp-port>`: client bind UDP local và báo port cho server để sử dụng active mode.
- `TYPE I`/`TYPE A` và `MODE S`/`B`/`C` quy định cách xử lý payload (nén với `MODE C`, newline conversion với `TYPE A`).

Trước `LIST`, `RETR`, `STOR` bạn phải cấu hình data channel (`PASV` hoặc `PORT`).

Ví dụ ngắn (client prompt):
```text
USER admin
PASS 123456
TYPE I
MODE S
PASV
STOR data\newdir\abc.txt    # upload
PASV
RETR newdir\abc.txt         # download
HASH newdir\abc.txt         # kiểm tra SHA-256 trên server
QUIT
```

## Kiểm chứng (logs, checksum, RDT traces)

- Control logs: `logs\server_run.log` và `logs\client_run.log` (ghi lệnh FTP và reply). Tìm các dòng chứa `PASV|PORT|STOR|RETR` và mã `125|150|226`.
- Checksum: server có lệnh `HASH <file>` trả `SHA-256 <name> <hash>`; client cũng tính SHA-256 sau `RETR` và so sánh.
- RDT/UDP: tiến trình truyền, SYN/ACK/FIN và retransmit được in ra terminal trong khi transfer — chụp màn hình những đoạn này làm minh chứng.

Ví dụ trích log (PowerShell):
```powershell
Select-String -Path logs\client_run.log -Pattern 'PASV|PORT|STOR|RETR|125|150|226' -SimpleMatch
Select-String -Path logs\server_run.log -Pattern 'PASV|PORT|STOR|RETR|125|150|226' -SimpleMatch
```

## Thư mục lưu trữ dữ liệu

- Server root theo code là `data/` (được tạo nếu chưa tồn tại).
- Client download mặc định: `data/client_downloads/`.
- Repository có `data/server_storage/` nhưng implementation mặc định dùng `data/` làm root; nếu bạn muốn server dùng thư mục khác, cần chỉnh `server/main_server.py`.

## Chạy test

Chạy các test unit có sẵn từ thư mục gốc:

```powershell
python tests/test_checksum.py
python tests/test_rdt_lossy.py
python -m unittest discover -s tests -p "test_*.py" -v
```

Hoặc chạy từng test cụ thể với `python -m unittest -v tests.test_active_upload` v.v.

## Điều cần biết (tổng quát, không theo thời gian)

- Data channel là UDP + RDT (Go-Back-N, cumulative ACK, fast retransmit); cửa sổ cố định tại 8 packets.
- Mỗi session chỉ có một transfer worker; control thread cho phép một số lệnh (ví dụ `ABOR`) trong lúc transfer.
- Hạn chế chính: upload/download có thể tiêu tốn RAM cho payload lớn; chưa có congestion control hay dải port cố định cho NAT traversal.

Chi tiết thiết kế và luồng hoạt động nằm trong [ARCHITECTURE.md](ARCHITECTURE.md).
