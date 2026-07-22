# Đồ Án Hybrid FTP Application

Hệ thống truyền tải tệp tin phân tách Control Plane (TCP) và Data Plane (UDP - RDT).

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

- Ứng dụng FTP hybrid tách riêng Control Plane (TCP) và Data Plane (UDP với cơ chế RDT).
- `server/main_server.py` là điểm khởi chạy cho máy chủ.
- `client/main_client.py` là điểm khởi chạy cho máy khách.
- `server/auth` chứa xử lý xác thực người dùng và dữ liệu người dùng mẫu.
- `server/control` xử lý lệnh điều khiển, mã FTP và phiên làm việc.
- `shared` chứa các module dùng chung: checksum, cấu trúc gói và RDT.
- `tests` chứa bài kiểm tra cho hàm checksum và kênh RDT mất gói.

## �👥 Phân công công việc
- **Thành viên A (Chủ trì Kênh Dữ liệu):** Chịu trách nhiệm gói `shared/` và môi trường `tests/`.
- **Thành viên B (Chủ trì Kênh Điều khiển):** Chịu trách nhiệm gói `server/` và `client/`.
