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

Giới hạn hiện tại:

- Download (`RETR`) và `LIST` hỗ trợ active hoặc passive mode.
- Upload (`STOR`, `STOU`, `APPE`) hiện chỉ hỗ trợ passive mode.
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

Mỗi lệnh truyền dữ liệu trả reply sơ bộ `125`/`150`, thực hiện truyền qua UDP/RDT, rồi trả reply hoàn tất `226` hoặc reply lỗi. `HELP` sử dụng FTP multiline reply (`214-...` đến `214 End`).

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
│   └── test_rdt_lossy.py
├── docs/
└── report/
```

Lưu ý: mặc dù repository có `data/server_storage/`, implementation hiện tại đặt `ClientSession.server_root` tại toàn bộ `data/`.

## Kiểm thử

```bash
python tests/test_checksum.py
python tests/test_rdt_lossy.py
```

Các test hiện là script dùng `assert`, không phải `unittest.TestCase`.
`test_rdt_lossy.py` kiểm tra RDT trong môi trường UDP giả lập mất gói và có tạo file mẫu trong `tests/`.

Chi tiết thiết kế và flow nằm trong [ARCHITECTURE.md](ARCHITECTURE.md).
