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

## 👥 Phân công công việc
- **Thành viên A (Chủ trì Kênh Dữ liệu):** Chịu trách nhiệm gói `shared/` và môi trường `tests/`.
- **Thành viên B (Chủ trì Kênh Điều khiển):** Chịu trách nhiệm gói `server/` và `client/`.
