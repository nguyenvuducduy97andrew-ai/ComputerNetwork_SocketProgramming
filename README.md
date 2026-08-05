# Hybrid FTP Client–Server

Ứng dụng truyền tệp theo mô hình Client–Server, tách thành hai kênh:

- **Control channel (TCP):** duy trì phiên, gửi lệnh FTP-like và nhận reply.
- **Data channel (UDP + RDT):** truyền listing và nội dung tệp bằng cơ chế Reliable Data Transfer tự cài đặt.

Client và server là hai package độc lập. Hai phía chỉ dùng chung các thành phần giao thức dữ liệu trong `shared/`.

## Yêu cầu

- Python 3.10 trở lên.
- Không cần cài thư viện ngoài Python standard library.
- Chạy các lệnh từ thư mục gốc của repository.

## Khởi chạy

Mở hai terminal riêng.

Server:

```bash
python -m server.main_server
```

Server mặc định lắng nghe TCP tại `0.0.0.0:2121` và dùng thư mục `data/` làm server root.

Client:

```bash
python -m client.main_client --host localhost --port 2121
```

Client lưu file tải về tại `data/client_downloads/`. Khi upload, client ưu tiên đường dẫn được nhập trực tiếp; nếu không tìm thấy, nó tìm trong `data/client_downloads/`.

Tài khoản được đọc từ `server/auth/user.json`.

### Chạy client và server trên hai máy

Hai máy cần kết nối vào cùng một mạng LAN. Trên máy server, xác định địa chỉ IPv4 bằng lệnh:

```powershell
ipconfig
```

Ví dụ, địa chỉ IPv4 của máy server là `192.168.1.10`. Tiếp theo, cấu hình firewall để cho phép TCP `2121` cho control channel và UDP cho data channel. Cách cấu hình chi tiết tùy thuộc vào hệ điều hành.

Trên Windows 11, mở PowerShell bằng quyền Administrator và chạy:

```powershell
New-NetFirewallRule -DisplayName "Hybrid FTP TCP 2121" -Direction Inbound -Protocol TCP -LocalPort 2121 -Action Allow
New-NetFirewallRule -DisplayName "Hybrid FTP UDP" -Direction Inbound -Protocol UDP -Action Allow
```

Sau đó, khởi chạy server:

```bash
python -m server.main_server
```

Trên máy client, nếu muốn dùng Active Mode, máy client cũng phải cho phép UDP inbound:
```powershell
New-NetFirewallRule -DisplayName "Hybrid FTP UDP" -Direction Inbound -Protocol UDP -Action Allow
```

Kết nối bằng địa chỉ IPv4 của máy server, không dùng `localhost`:

```bash
python -m client.main_client --host 192.168.1.10 --port 2121
```

Các điều kiện mạng cần đáp ứng:

- firewall máy server cho phép TCP `2121` cho control channel;
- firewall hai máy cho phép UDP vì data channel dùng RDT trên UDP;
- passive mode yêu cầu client truy cập được cổng UDP động do server mở;
- active mode yêu cầu server truy cập được cổng UDP động do client mở;
- địa chỉ loopback `127.0.0.1`/`localhost` chỉ dùng khi hai tiến trình chạy trên cùng máy.

Trong mạng LAN, server lấy IP active của client từ TCP peer và lệnh `PORT` chỉ truyền số cổng. Khi hai máy ở sau các NAT/router khác nhau, cấu hình hiện tại chưa phù hợp để chạy trực tiếp qua Internet: dự án chưa có dải passive UDP port cố định, advertised public IP hoặc cơ chế NAT traversal. Khi đó cần cấu hình firewall/port-forward cho TCP `2121` và một dải UDP cố định trước.

## Các lệnh được hỗ trợ

| Nhóm | Lệnh |
|---|---|
| Xác thực và phiên | `USER`, `PASS`, `QUIT`, `NOOP`, `HELP` |
| Thư mục | `PWD`, `CWD`, `CDUP`, `MKD`, `RMD` |
| Listing và metadata | `LIST`, `NLST`, `STAT`, `SIZE`, `MDTM` |
| Thiết lập truyền | `TYPE`, `MODE`, `PORT`, `PASV` |
| Truyền dữ liệu | `RETR`, `STOR`, `STOU`, `APPE`, `ABOR` |
| Quản lý tệp | `DELE`, `RNFR`, `RNTO`, `HASH` |

`USER`, `PASS`, `QUIT`, `NOOP` và `HELP` được phép trước khi đăng nhập. Các lệnh còn lại yêu cầu phiên đã xác thực.

### Thiết lập data channel

- `TYPE I`: truyền nhị phân, là giá trị mặc định.
- `TYPE A`: chuẩn hóa newline của văn bản UTF-8.
- `MODE S` và `MODE B`: hiện cùng truyền payload không nén.
- `MODE C`: nén/giải nén payload bằng `zlib`.
- `PORT <port>`: chọn active UDP và cung cấp cổng UDP của client.
- `PASV`: server mở một UDP socket và trả `UDP_PORT=<port>`.

Trạng thái hiện tại:

- Download (`RETR`, `LIST`) và upload (`STOR`, `STOU`, `APPE`) đều hỗ trợ active hoặc passive mode.
- Trong active upload, server tạo UDP receive socket, gửi `SYN` đến endpoint do client đăng ký và chỉ nhận dữ liệu sau khi nhận `SYN|ACK` hợp lệ.
- Mỗi TCP session chỉ có tối đa một file transfer đang chạy. Server vẫn phục vụ nhiều client đồng thời bằng một thread control cho mỗi connection và một worker cho transfer của session đó.
- Trong khi transfer đang chạy, chỉ `ABOR`, `NOOP`, `STAT` và `QUIT` được chấp nhận; các command khác nhận `503`.
- Data channel là UDP/RDT, vì vậy cú pháp `PORT` và reply `PASV` là biến thể của dự án, không phải cú pháp địa chỉ sáu số của FTP chuẩn.

Ví dụ một phiên:

```text
USER alice
PASS secret
TYPE I
MODE S
PASV
LIST
RETR example.bin
QUIT
```

Mỗi lệnh truyền dữ liệu trả reply sơ bộ `125`/`150`; worker thực hiện truyền qua UDP/RDT rồi tự gửi reply hoàn tất `226` hoặc reply lỗi `426` trên control connection. Control thread quay lại `recv()` ngay sau reply sơ bộ để có thể nhận các command được phép trong lúc truyền. `HELP` sử dụng FTP multiline reply (`214-...` đến `214 End`).

### Hạn chế đã biết

- Client CLI hiện xử lý transfer đồng bộ, nên khó nhập `ABOR` tương tác từ chính cửa sổ client trong lúc handler đang chờ transfer; server đã có cancellation nhưng client cần tách luồng nhập/control để khai thác đầy đủ.
- RDT dùng cửa sổ cố định và chưa có tổng deadline/số lần retry tối đa cho toàn bộ transfer.
- Upload/download hiện có thể nạp toàn bộ payload vào RAM, chưa tối ưu cho file lớn.
- Chưa có khóa theo file; hai session khác nhau có thể thao tác cùng một đường dẫn.
- Cổng UDP passive/active được cấp động, chưa có cấu hình dải port dành cho triển khai qua NAT.

## Cấu trúc dự án

```text
.
├── README.md
├── ARCHITECTURE.md
├── client/
│   ├── main_client.py
│   └── control/
│       ├── client_control.py
│       ├── command_handler.py
│       ├── context.py
│       ├── data_transfer_service.py
│       ├── cli_monitor.py
│       └── handlers/
│           ├── auth_handler.py
│           ├── common.py
│           ├── navigation_handler.py
│           ├── transfer_setup_handler.py
│           ├── transfer_handler.py
│           └── file_handler.py
├── server/
│   ├── main_server.py
│   ├── auth/
│   │   ├── user_db.py
│   │   └── user.json
│   └── control/
│       ├── command_handler.py
│       ├── command_result.py
│       ├── data_transfer_service.py
│       ├── ftp_codes.py
│       ├── session.py
│       └── handlers/
│           ├── auth_handler.py
│           ├── common_handler.py
│           ├── navigation_handler.py
│           ├── transfer_setup_handler.py
│           ├── transfer_handler.py
│           └── file_handler.py
├── shared/
│   ├── checksum.py
│   ├── constants.py
│   ├── packet_struct.py
│   └── rdt_core.py
├── data/
│   ├── client_downloads/
│   └── server_storage/
├── tests/
│   ├── test_checksum.py
│   ├── test_rdt_lossy.py
│   ├── test_active_upload.py
│   ├── test_rdt_peer_filtering.py
│   └── test_transfer_cancellation_cleanup.py
├── docs/
└── report/
```

Lưu ý: mặc dù repository có `data/server_storage/`, implementation hiện tại đặt `ClientSession.server_root` tại toàn bộ `data/`.

## Kiểm thử

```bash
python tests/test_checksum.py
python tests/test_rdt_lossy.py
python tests/test_active_upload.py
python tests/test_rdt_peer_filtering.py
python tests/test_transfer_cancellation_cleanup.py
```

Mỗi lệnh trên chạy một nhóm kiểm thử độc lập, đều hỗ trợ chạy trực tiếp bằng cú pháp `python tests/<tên_file>.py`.
`test_rdt_lossy.py` kiểm tra RDT trong môi trường UDP giả lập mất gói và có tạo file mẫu tạm trong `tests/`.


Chi tiết thiết kế và flow nằm trong [ARCHITECTURE.md](ARCHITECTURE.md).
