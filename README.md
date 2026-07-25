# Đồ Án Hybrid FTP Application

Ứng dụng truyền tải tệp tin theo mô hình Hybrid FTP, trong đó kênh điều khiển dùng TCP để xử lý đăng nhập và lệnh FTP-like, còn kênh dữ liệu dùng UDP kết hợp cơ chế RDT để truyền tệp tin ổn định hơn trong môi trường mạng không tin cậy.

## Vai trò của từng thành phần

### Client
- Là điểm khởi chạy phía người dùng để kết nối tới server và gửi các lệnh điều khiển.
- Cung cấp lớp điều khiển CLI để tương tác với server và hiển thị trạng thái truyền nhận.
- Hỗ trợ các phần dùng chung để kiểm tra checksum, cấu trúc gói tin và theo dõi tiến trình truyền file.

### Server
- Lắng nghe kết nối TCP và quản lý từng phiên làm việc của client.
- Xử lý xác thực người dùng, điều hướng thư mục, thiết lập chế độ truyền và các lệnh FTP cơ bản như `USER`, `PASS`, `PWD`, `CWD`, `CDUP`, `TYPE`, `MODE`, `RETR`, `STOR`, `QUIT`.
- Quản lý trạng thái truyền file, thư mục làm việc, và logic cho kênh dữ liệu UDP/RDT.

## 🚀 Hướng dẫn khởi chạy nhanh

### 1. Phía Máy chủ (Server)
```bash
python server/main_server.py
```

### 2. Phía Máy khách (Client)
```bash
python client/main_client.py
```

## Cấu trúc dự án

- README.md
- client/
  - __init__.py
  - main_client.py
  - control/
    - __init__.py
    - client_control.py
    - ui_monitor.py
- server/
  - __init__.py
  - main_server.py
  - auth/
    - __init__.py
    - user_db.py
    - user.json
  - control/
    - __init__.py
    - command_handler.py
    - ftp_codes.py
    - session.py
    - handlers/
      - __init__.py
      - auth_handler.py
      - navigation_handler.py
      - transfer_setup_handler.py
      - transfer_handler.py
- shared/
  - __init__.py
  - checksum.py
  - constants.py
  - packet_struct.py
  - rdt_core.py
- data/
  - client_downloads/
  - server_storage/
- tests/
  - test_checksum.py
  - test_rdt_lossy.py
- docs/
  - genai_audit_log.md
- report/
  - diagrams/

## 🧭 Trạng thái hiện tại

- Ứng dụng được chia thành hai phần rõ ràng: client cho tương tác người dùng và server cho xử lý nghiệp vụ truyền file. Tách riêng Control Plane (TCP) và Data Plane (UDP với cơ chế RDT).
- `server/main_server.py` là điểm khởi chạy cho máy chủ TCP và vòng lặp xử lý từng client theo luồng riêng.
- `client/main_client.py` là điểm khởi chạy cho phía client.
- `server/auth` chứa xác thực người dùng và dữ liệu tài khoản mẫu.
- `server/control` chứa bộ xử lý lệnh FTP-like, mã phản hồi và trạng thái phiên.
- `shared` chứa các thành phần dùng chung cho checksum, cấu trúc gói tin và lõi RDT.
- `tests` chứa kiểm thử cho checksum và hành vi truyền trên kênh RDT trong môi trường mất gói.

## �👥 Phân công công việc
- **Thành viên A (Chủ trì Kênh Dữ liệu):** Chịu trách nhiệm gói `shared/` và môi trường `tests/`.
- **Thành viên B (Chủ trì Kênh Điều khiển):** Chịu trách nhiệm gói `server/` và `client/`.
