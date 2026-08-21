## Kiến trúc (tóm tắt hiện trạng)

Tài liệu này tóm tắt cấu trúc và luồng chính của dự án theo code hiện tại.

Thành phần chính:
- `server/`: TCP control server, session, handlers và data-transfer facade.
- `client/`: CLI client, control helper, data-transfer client và handlers.
- `shared/`: packet format, checksum và module RDT (reliable UDP transfer).

Thiết kế chính:
- Control plane: một TCP connection cho mỗi client; server lắng nghe `2121`; mỗi connection xử lý bởi một thread với `ClientSession`.
- Data plane: UDP + RDT (Go-Back-N, cumulative ACK, fast retransmit, FIN handshake). Data channel có hai chế độ: `ACTIVE` (client báo port bằng `PORT`) hoặc `PASSIVE` (`PASV` — server bind UDP port và trả `UDP_PORT=<port>`).
- Transfer workflow: handlers trả reply sơ bộ (`125`/`150`), khởi worker thread thực hiện UDP/RDT, worker gửi reply hoàn tất (`226`/`426`) qua control socket.

Các điểm cần biết khi vận hành và kiểm thử:
- Server root là `data/server_storage/`; client lưu download vào vùng riêng `data/client_downloads/`.
- Trước mỗi `LIST`/`RETR`/`STOR`/`STOU`/`APPE` phải cấu hình data channel mới bằng `PASV` hoặc `PORT`.
- `HASH <file>` trả SHA-256 từ server; client so sánh hash sau `RETR`, `STOR` và `STOU` ở `TYPE I`. `TYPE A` bỏ qua byte hash vì có chuẩn hóa newline; `APPE` không tự hash vì payload local chỉ là phần nối thêm.
- Các lệnh hỗ trợ đầy đủ: xác thực (`USER`/`PASS`), quản lý file (`STOR`/`RETR`/`DELE`/`RNFR`/`RNTO`/`HASH`), listing (`LIST`/`NLST`) và thiết lập truyền (`TYPE`/`MODE`/`PORT`/`PASV`).

Hạn chế vận hành quan trọng:
- Codec vẫn xử lý toàn payload trong RAM; RDT không còn giữ thêm danh sách chunks/packets nhưng hệ thống vẫn phù hợp nhất với file cỡ vừa.
- Chưa có congestion control hay dải UDP cố định cho NAT traversal.
- `ABOR` đánh dấu hủy, đóng data socket và thay thế final reply của worker bằng một reply xác nhận duy nhất; worker không gửi thêm reply muộn làm lệch control channel.

Kiểm thử:
- Các test nằm trong `tests/` (checksum, RDT lossy, active upload, peer filtering, cancellation, upload completion). Chạy từ root:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Tài liệu tham khảo chi tiết: `README.md` (tóm tắt chạy nhanh) và mã nguồn trong `client/` và `server/`.

---

## Tài liệu chi tiết (phiên bản hiện tại)

Mục đích của phần này là mô tả chi tiết hành vi, API nội bộ, luồng dữ liệu và những nơi cần kiểm tra khi vận hành/kiểm thử. Nội dung phản ánh mã nguồn hiện có, không bao gồm lịch sử hay thay đổi theo thời gian.

1) Tổng quan cấu trúc mã
- `server/main_server.py`: entrypoint server, lắng nghe TCP 2121, spawn thread cho mỗi kết nối control.
- `server/control/*`: handlers, session, ftp_codes, data_transfer_service (facade server-side), command_result.
- `client/main_client.py`: entrypoint client, mở TCP control, vòng CLI `ftp>`.
- `client/control/*`: `client_control.py` (TCP helpers), `command_handler.py` (dispatch CLI -> handlers), `data_transfer_service.py` (client-side payload processing), `context.py` (ClientContext), `cli_monitor.py` (progress UI).
- `shared/*`: `constants.py` (packet/header/TCP/UDP constants), `packet_struct.py` (pack/unpack header+payload), `rdt_core.py` (reliable send/recv), `block_mode.py` (MODE B framing), `checksum.py` (file SHA-256 helper used by `HASH`).

2) Control channel (TCP) — chi tiết

- Kết nối: client tạo TCP connection tới host:port; server chấp nhận, gửi greeting 220.
- Giao thức lệnh: mỗi lệnh CRLF-terminated ("CMD arg...\r\n"). Server đọc cho tới CRLF và xử lý một dòng.
- Server dispatch/handler: `server/control/command_handler.py` kiểm tra authentication, transfer_in_progress, và gọi handler tương ứng.
- Reply model: handler có thể trả 1 reply string (ví dụ `230 User logged in.`) hoặc iterator `CommandReplies` (dùng cho multi-stage replies). `iter_command_replies()` chuẩn hóa.

3) Command handling — hành vi server/client

- Authentication: `USER <name>` → server trả 331 hoặc 530; `PASS <pwd>` → 230 on success.
- Commands allowed before login: `USER`, `PASS`, `QUIT`, `NOOP`, `HELP`.
- Commands during transfer: server cho phép `ABOR`, `NOOP`, `STAT`, `QUIT`; CLI client chỉ nhận `ABOR` trong lúc worker dữ liệu chạy để giữ một nơi duy nhất đọc reply trên control channel.
- Transfer commands (`RETR`, `STOR`, `STOU`, `APPE`) luôn:
	1. validate path/permissions
	2. validate data connection config via `validate_data_connection(session, direction=...)`
	3. prepare outgoing/incoming data (codec apply TYPE/MODE)
	4. yield preliminary reply `125`/`150` (includes BYTES=nnn for RETR)
	5. start worker thread `session.run_transfer(worker_fn)`
	6. worker performs UDP/RDT, sets `session.transferred_bytes`, and sends final reply `226` (or `426`/`451` on error)
- `STOU` sinh tên `file_<uuid>.dat`, công bố tên qua `REMOTE_NAME` trong cả reply `150` và `226`; client dùng tên này cho `HASH` sau upload.
- `APPE` không chạy `HASH` tự động. Reply hoàn tất chứa `APPENDED_BYTES` và `FINAL_SIZE` để phân biệt lượng dữ liệu vừa nối với kích thước toàn bộ file.
- `MODE B` dùng header 3 byte `descriptor:uint8 + count:uint16`, theo sau bởi data block; block cuối mang descriptor EOF.

4) Session lifecycle và state transitions

- `ClientSession` (server-side) chứa: authentication, current_directory, transfer_type, transfer_mode, data_connection_mode, active_udp_address, passive_udp_socket, passive_client_address, current_data_socket, transfer_in_progress, transfer_thread, cancel_event, conn_send_lock.
- `start_transfer()` thiết lập state; `finish_transfer()` reset. `request_abort()` set cancel_event; `close_current_data_socket()` đóng socket.

5) Data channel (UDP + RDT) — chi tiết kỹ thuật

- Packet header: `!IIHHB` (seq:uint32, ack:uint32, checksum:uint16, length:uint16, flags:uint8) — tổng 13 bytes header.
- Payload max: 1024 bytes; `BUFFER_SIZE = HEADER_SIZE + MAX_PAYLOAD`.
- Flags: `FLAG_SYN`, `FLAG_ACK`, `FLAG_FIN`, `FLAG_DATA`.
- RDT algorithm (`shared/rdt_core.py`):
	- Sender: Go-Back-N with WINDOW_SIZE = 8.
	- Receiver: cumulative ACK; send ACK with ack = next expected seq.
	- Fast retransmit on DUP_ACK_THRESHOLD = 3.
	- RTO = TIMEOUT (0.3s); DATA_MAX_RETRIES = 10 và bộ đếm reset khi cumulative ACK làm cửa sổ tiến lên.
	- Receiver dừng với `RDTDataTimeout` sau 10 RTO liên tiếp không nhận DATA hợp lệ; sender cũng phát lỗi này khi DATA hết retry.
	- FIN handshake có FIN_MAX_RETRIES = 10 và receiver linger 0.6s.
	- `reliable_send()` giữ một bản payload, đóng gói từng packet theo nhu cầu và theo dõi ACK mà không nhân đôi toàn bộ chunks/packets trong RAM.
	- `reliable_recv()` chỉ append DATA đúng thứ tự vào một byte buffer, responds ACKs, và trả full payload bytes (hoặc ghi file nếu có path).

6) Active vs Passive (handshake details)

- Passive (`PASV`):
	- server: create UDP socket, bind('', 0), session.passive_udp_socket = sock, return `227 ... UDP_PORT=<port>`.
	- client: session.ensure_data_socket(); session.data_connection_mode='PASSIVE'; session.data_peer_address=(server_host, port).
	- before data transfer, client sends a SYN probe and waits for SYN-ACK; it retries up to 5 times (1 second/attempt).
	- after discovery, passive server sender still responds to duplicate SYN, so a lost first SYN-ACK can be recovered while DATA retransmission continues.

- Active (`PORT <udp-port>`):
	- client: ensure UDP socket bound to specified local port; send `PORT <port>` to server.
	- server: session.active_udp_address = (tcp_peer_ip, port); when sending, server creates ephemeral UDP socket and contacts that address; when receiving, server performs SYN handshake as implemented in `_open_active_receive_channel()`.

7) File paths and where files are read/written

- Server root: `server_root = (Path('data') / 'server_storage').resolve()` trong `run_server()`; đây là root cho `RETR`, `STOR`, `DELE`, `RNFR`.
- Client upload resolution: client `handle_stor` uses `_resolve_local_upload_path()` which checks given path directly first (absolute/relative), otherwise falls back to `data/client_downloads/<filename>`.
- Client download destination: `data/client_downloads/<filename>` (created if missing).

8) Logging locations and useful grep patterns

- Server runtime log (stdout redirected if you run with `Tee-Object`): `logs/server_run.log`.
- Client runtime log: `logs/client_run.log`.
- Useful search patterns:
	- Control commands & replies: `PASV|PORT|STOR|RETR|STOU|APPE|125|150|226|426|230|331|220`
	- RDT handshake/flow: `SYN|ACK|FIN|retransmit|transfer|Receiving|Starting transfer|transferred` (case-insensitive)

9) Tests (chi tiết chạy & ý nghĩa)

- `tests/test_checksum.py`: kiểm tra hàm SHA-256 và helper checksum.
- `tests/test_rdt_lossy.py`: mô phỏng mất gói (20%) để kiểm tra retransmit, FIN behavior và tái ghép payload.
- `tests/test_active_upload.py`: mô phỏng upload active end-to-end.
- `tests/test_rdt_peer_filtering.py`: đảm bảo receiver loại bỏ gói từ peer không mong đợi.
- `tests/test_transfer_cancellation_cleanup.py`: kiểm tra `ABOR` và cleanup thread/socket/session.
- `tests/test_appe_stou.py`: kiểm tra `APPE` không hash sai phạm vi, metadata kích thước, tên UUID của `STOU` và hash theo `REMOTE_NAME`.
- `tests/test_demo_readiness.py`: kiểm tra MODE B hai chiều, storage tách biệt, HELP STOU, STAT file, MDTM UTC và hash semantics của TYPE A.
- `tests/test_passive_handshake_retry.py`: mô phỏng mất SYN probe và mất SYN-ACK để bảo vệ LIST/RETR/STOR/STOU/APPE trên Wi-Fi.

Chạy toàn bộ suite:
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

10) Hướng dẫn thu minh chứng upload/download (chi tiết từng bước để bạn chụp ảnh/log)

- Bước chuẩn bị: từ workspace root, mở hai terminal PowerShell.

- Terminal A (server):
```powershell
cd 'c:\Users\PC\OneDrive\Máy tính\MMT_Projects_SocketPrograming'
New-Item -ItemType Directory -Force logs | Out-Null
python -u -m server.main_server 2>&1 | Tee-Object -FilePath logs\server_run.log
```
	- Chụp/ghi lại dòng: "Starting Hybrid FTP Server on 0.0.0.0:2121" và "Server root directory: <abs path>".

- Terminal B (client):
```powershell
cd 'c:\Users\PC\OneDrive\Máy tính\MMT_Projects_SocketPrograming'
New-Item -ItemType Directory -Force logs | Out-Null
python -u -m client.main_client --host localhost --port 2121 2>&1 | Tee-Object -FilePath logs\client_run.log
```
	- Ở prompt `ftp>` thực hiện:
		1. `USER admin` — chụp reply (331)
		2. `PASS 123456` — chụp reply (230)
		3. `TYPE I` / `MODE S`
		4. `PASV` — chụp reply `227 ... UDP_PORT=<port>` (ghi port)
		5. `STOR abcabc.txt` — client đọc `data\client_downloads\abcabc.txt`; chụp preliminary `150`, progress bar và final `226`.
		6. Trên server terminal: chụp log nơi `Started thread`/`Sent reply 226` xuất hiện; kiểm tra `data\server_storage\abcabc.txt`.
		7. Chạy lại `PASV`, rồi `RETR abcabc.txt`; kiểm tra file tải về ở `data\client_downloads\abcabc.txt`.

- Kiểm tra checksum:
```powershell
Get-FileHash data\server_storage\abcabc.txt -Algorithm SHA256
Get-FileHash data\client_downloads\abcabc.txt -Algorithm SHA256
```
	- Chụp màn hình giá trị hash và lưu vào minh chứng.

- Trích control logs (sau khi chạy xong):
```powershell
Select-String -Path logs\client_run.log -Pattern 'PASV|PORT|STOR|RETR|125|150|226' -SimpleMatch | Out-File docs\minh_chung\client_control_lines.txt
Select-String -Path logs\server_run.log -Pattern 'PASV|PORT|STOR|RETR|125|150|226' -SimpleMatch | Out-File docs\minh_chung\server_control_lines.txt
```
	- (Nếu bạn không muốn tạo files tự động, thay `Out-File` bằng copy/paste thủ công.)

11) Bố cục storage khi chạy cùng máy

- Server chỉ truy cập `data/server_storage/` thông qua session path resolver.
- Client tìm file upload trực tiếp theo argument trước; nếu không thấy thì fallback về `data/client_downloads/<filename>`.
- Việc tách hai root giúp `LIST` phía server không vô tình hiển thị file download cục bộ của client.

12) Debugging & phát triển

- Để bật nhiều log hơn, bạn có thể thêm `print()` tạm thời trong các module `server/control/data_transfer_service.py`, `shared/rdt_core.py` hoặc `client/control/data_transfer_service.py` tại các điểm handshake (SYN/ACK/FIN) và khi retransmit.
- Để thu packet-level traces bên ngoài mã: dùng `Wireshark` lọc UDP theo port trả về trong `PASV` hoặc theo UDP peer IP/port trong chế độ active.

13) Bảo mật & lưu ý vận hành

- Mật khẩu plaintext trong `server/auth/user.json` là ví dụ; không dùng trong môi trường thực.
- Control channel không được mã hóa (plaintext TCP) — tránh chạy trên network công cộng mà không có TLS.
- DNS/nAT: passive/active UDP dynamic port chưa sẵn sàng cho môi trường đa-NAT.

14) Kết luận

- Tài liệu này mô tả chi tiết hành vi runtime, giao diện lệnh và nơi tra cứu log/test cần thiết cho minh chứng upload/download.
- Nếu bạn muốn, mình có thể tiếp tục: (A) tạo `docs/minh_chung/` templates (README + log extraction scripts), hoặc (B) thêm phần mô tả API chi tiết cho từng hàm/klase trong `server/control/` và `client/control/`.

