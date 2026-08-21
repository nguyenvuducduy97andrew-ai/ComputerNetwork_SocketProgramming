# Hướng dẫn thực hiện Project 2: Wireshark – FTP và HTTP Traffic Analysis

Tài liệu này tổng hợp yêu cầu trong đề `Project2_wireshark_2026.docx.pdf`, cách áp dụng vào đồ án Hybrid FTP của Project 01, quy trình capture Wireshark, danh sách ảnh minh chứng, dữ liệu cần chuẩn bị, các file cần nộp và cách trả lời phần câu hỏi phân tích.

Các thông tin kỹ thuật của Project 01 được đối chiếu với [`README.md`](../README.md), [`ARCHITECTURE.md`](../ARCHITECTURE.md), [`shared/constants.py`](../shared/constants.py), [`shared/packet_struct.py`](../shared/packet_struct.py) và [`server/auth/user.json`](../server/auth/user.json).

---

## 1. Giải đáp quan trọng: có phải trả lời hết danh sách câu hỏi không?

**Có. Nên trả lời đầy đủ tất cả câu hỏi trong các mục Analysis Questions/Experiments của đề.**

- Part 1 – FTP: trả lời các câu hỏi về connection, authentication, directory listing, upload và download trên FTP công cộng. Sau đó trả lời/phân tích lại dựa trên client/server Project 01, bao gồm so sánh Active Mode với Passive Mode và vấn đề lộ credential.
- Part 2 – HTTP: trả lời đủ các câu hỏi 1–24 về DNS, TCP handshake, HTTP request, HTTP response, segmentation/reassembly, đóng kết nối và vòng đời hoàn chỉnh của request.

Mỗi câu trả lời nên có bốn thành phần:

1. Câu trả lời trực tiếp.
2. Số packet dùng làm bằng chứng.
3. Field/value lấy từ packet.
4. Mã hình minh chứng, nếu câu đó cần bằng chứng trực quan.

Ví dụ:

> **Câu hỏi: Server sử dụng TCP port nào?**  
> Server sử dụng TCP port `80`. Trong packet `No. 17` là SYN/ACK, trường `Source Port: 80` chứng minh server trả lời từ cổng HTTP. Xem Hình H2-02.

Không bắt buộc mỗi câu phải có một ảnh riêng. Một ảnh có thể dùng cho nhiều câu liên quan. Ví dụ ảnh TCP handshake có thể đồng thời chứng minh:

- Client/server IP.
- Client ephemeral port và server port.
- SYN, SYN/ACK và ACK.
- Sequence/Acknowledgment number.
- MSS và Window Size.

Trong từng câu chỉ cần dẫn lại đúng mã hình. Không nên bỏ câu chỉ vì câu đó có vẻ trùng với câu trước.

Hai phần rất dễ bị bỏ sót:

- Sau FTP công cộng, đề còn yêu cầu phân tích dựa trên client/server Project 01 chạy trên hai máy.
- Câu 24 của Part 2 yêu cầu viết một đoạn mô tả vòng đời theo thứ tự `DNS → TCP handshake → HTTP request → HTTP response → connection close`.

---

## 2. Tổng quan các phần phải thực hiện

Project 2 gồm hai phần, mỗi phần 50 điểm.

### Part 1 – FTP Protocol Analysis

1. Capture FTP công cộng tại `ftp.dlptest.com`.
2. Phân tích connection, login, directory listing, upload và download.
3. Chạy lại thí nghiệm với chính Project 01 trên hai máy khác nhau.
4. Capture riêng Active Mode và Passive Mode.
5. So sánh hai mode và phân tích cleartext credential.

### Part 2 – HTTP Protocol Analysis

1. Tự viết raw TCP socket client.
2. Kết nối `www.google.com:80`.
3. Gửi HTTP/1.1 GET request bằng chuỗi tự tạo.
4. Capture DNS, TCP handshake, HTTP request/response, segmentation/reassembly và connection teardown.
5. Trả lời toàn bộ câu hỏi 1–24.

Nên tạo bốn capture riêng:

| File capture | Nội dung |
|---|---|
| `part1_public_ftp.pcapng` | FTP công cộng `ftp.dlptest.com` |
| `part1_project01_active.pcapng` | Project 01 chạy Active Mode |
| `part1_project01_passive.pcapng` | Project 01 chạy Passive Mode |
| `lab_capture.pcapng` | Raw HTTP socket tới `www.google.com:80` |

---

## 3. Cấu trúc thư mục nộp bài đề xuất

```text
Project2_GroupXX/
├── report/
│   └── Project2_GroupXX.pdf
├── captures/
│   ├── part1_public_ftp.pcapng
│   ├── part1_project01_active.pcapng
│   ├── part1_project01_passive.pcapng
│   └── lab_capture.pcapng
├── source/
│   └── http_client.py
├── data/
│   ├── ftp_upload_groupXX.jpg
│   ├── active_test.sent.bin
│   ├── active_test.downloaded.bin
│   ├── passive_test.sent.bin
│   ├── passive_test.downloaded.bin
│   └── hashes.txt
└── network_info.txt
```

Trong `network_info.txt`, ghi lại:

```text
Group:
Thời gian capture:

Client IPv4:
Server IPv4:
Wireshark interface:

FTP public hostname: ftp.dlptest.com
FTP public server IP:

Project01 TCP control port: 2121
Active UDP port: 50001
Passive UDP ports theo từng transfer:

HTTP hostname: www.google.com
Google IPv4 được sử dụng:
HTTP client ephemeral port:
TCP stream number:
```

Các giá trị IP, passive port, ephemeral port, stream number và packet number phải lấy từ capture thực tế, không chép số ví dụ trong tài liệu này.

---

## 4. Quy tắc capture và chụp ảnh minh chứng

### 4.1 Quy trình capture chung

1. Đóng client/kết nối cũ trước khi bắt đầu.
2. Mở Wireshark.
3. Chọn đúng interface đang có traffic, thường là Wi-Fi hoặc Ethernet.
4. Bắt đầu capture trước khi mở connection.
5. Thực hiện đúng một kịch bản đã định sẵn.
6. Đóng connection một cách bình thường nếu có thể.
7. Dừng capture ngay sau khi hoàn thành.
8. Lưu đúng tên `.pcapng`.
9. Mở lại file vừa lưu để chắc chắn file không rỗng và đọc được.

Không nên đặt capture filter quá hẹp nếu chưa biết cổng động. Có thể capture rộng rồi dùng display filter sau.

### 4.2 Yêu cầu đối với mỗi ảnh Wireshark

Theo đề, mỗi ảnh dùng làm bằng chứng phải:

- Thấy rõ cột `No.` và số packet.
- Thấy display filter đang sử dụng.
- Chọn đúng packet cần phân tích.
- Mở rộng đúng protocol/field trong Packet Details.
- Khoanh, đóng khung hoặc highlight field/value trả lời câu hỏi.
- Có caption rõ ràng bên dưới ảnh.

Ví dụ caption:

> **Hình P1-03 – Packet 48:** Lệnh `PASS` và reply `230`, chứng minh credential được gửi ở dạng cleartext.

Một ảnh có thể hỗ trợ nhiều câu hỏi, nhưng các giá trị cần thiết phải nhìn thấy được hoặc được đánh dấu rõ.

---

# PART 1 – FTP PROTOCOL ANALYSIS

## 5. Part 1A – FTP công cộng bằng FileZilla

### 5.1 Chuẩn bị file upload

Chuẩn bị một ảnh nhỏ khoảng 100–500 KB:

```text
ftp_upload_groupXX.jpg
```

Không sử dụng ảnh chứa thông tin nhạy cảm.

### 5.2 Cấu hình FileZilla

Mở `File → Site Manager → New Site` và cấu hình:

```text
Protocol: FTP - File Transfer Protocol
Host: ftp.dlptest.com
Port: 21
Encryption: Only use plain FTP (insecure)
Logon Type: Normal
User: dlpuser
Password: rNrKYTX9g7z3RgJRmxWuGHbeu
```

Đây là credential ghi trong đề. Nếu credential test không còn hiệu lực tại thời điểm thực hiện, dùng credential mới do DLP Test cung cấp và ghi rõ credential thực tế đã dùng trong phần cấu hình thí nghiệm.

Phải chọn plain FTP. Nếu dùng FTPS hoặc SFTP thì Wireshark không hiển thị cleartext command/credential như đề yêu cầu.

### 5.3 Bắt đầu capture

1. Chưa kết nối FileZilla.
2. Mở Wireshark và chọn Wi-Fi/Ethernet đang truy cập Internet.
3. Không đặt capture filter quá hẹp vì FTP data có thể dùng cổng động.
4. Nhấn Start Capture.
5. Sau đó mới kết nối FileZilla.

### 5.4 Chuỗi thao tác FTP công cộng

Thực hiện trong cùng một capture:

1. Kết nối `ftp.dlptest.com`.
2. Đăng nhập.
3. Tạo thư mục riêng, ví dụ `GroupXX_20260813`.
4. Mở thư mục vừa tạo.
5. Upload `ftp_upload_groupXX.jpg`.
6. Refresh/list thư mục để chứng minh file đã xuất hiện.
7. Download lại file.
8. Disconnect/QUIT.
9. Dừng capture.
10. Lưu thành `part1_public_ftp.pcapng`.

### 5.5 Display filter FTP công cộng

Chỉ xem command/reply trên control channel:

```wireshark
ftp
```

Xem FTP data:

```wireshark
ftp-data
```

Xem toàn bộ control connection:

```wireshark
tcp.port == 21
```

Tìm TCP handshake:

```wireshark
tcp.port == 21 && tcp.flags.syn == 1
```

Kiểm tra retransmission:

```wireshark
tcp.analysis.retransmission
```

Tìm đóng connection:

```wireshark
tcp.flags.fin == 1 || tcp.flags.reset == 1
```

Nếu Wireshark không tự nhận diện FTP data, xác định data port từ reply `PASV`/`EPSV`, sau đó dùng:

```wireshark
tcp.port == <data_port>
```

Với classic PASV reply dạng `(h1,h2,h3,h4,p1,p2)`, data port được tính bằng:

```text
data_port = p1 × 256 + p2
```

Với EPSV, server thường trả trực tiếp port trong dạng `|||port|`.

### 5.6 Checklist ảnh FTP công cộng

#### P1-01 – TCP handshake

Filter:

```wireshark
tcp.port == 21 && tcp.flags.syn == 1
```

Khoanh:

- Client IP.
- Server IP.
- Client ephemeral port.
- Server port `21`.
- SYN và SYN/ACK.

#### P1-02 – Authentication cleartext

Chọn packet port 21 → `Follow → TCP Stream`.

Khoanh:

```text
USER dlpuser
PASS ...
230 ...
```

#### P1-03 – Directory listing

Khoanh:

- `PASV` hoặc `EPSV`.
- `LIST`, `NLST` hoặc `MLSD` thực tế được FileZilla dùng.
- Reply `150`/`125`.
- Data port.
- Reply hoàn tất `226`.

#### P1-04 – Upload

Khoanh:

- `STOR ftp_upload_groupXX.jpg`.
- Reply `150`/`125`.
- Data connection.
- Reply `226`.

#### P1-05 – Download

Khoanh:

- `RETR ftp_upload_groupXX.jpg`.
- Reply `150`/`125`.
- Data connection.
- Reply `226`.

#### P1-06 – Đóng kết nối

Khoanh:

- `QUIT`.
- Reply `221` nếu có.
- FIN/ACK hoặc RST.

### 5.7 Nội dung phải trả lời cho FTP công cộng

Dùng giá trị và số packet trong capture thực tế để trả lời:

- FTP control connection dùng port nào?
- Client IP và server IP là gì?
- Packet nào bắt đầu connection?
- Ba packet TCP handshake là những packet nào?
- Connection kéo dài bao lâu?
- Có retransmission không?
- Lệnh nào gửi username?
- Lệnh nào gửi password?
- Reply nào cho biết login thành công?
- Vì sao việc nhìn thấy password trong Wireshark là nguy hiểm?
- Lệnh nào yêu cầu directory listing?
- Reply nào xuất hiện trước khi mở data connection?
- Data port là gì và được xác định như thế nào?
- Control connection và data connection khác nhau thế nào?
- Lệnh nào upload file?
- Lệnh nào download file?
- File nào được truyền và kích thước bao nhiêu?
- Data đi qua connection nào?
- Bên nào khởi tạo data connection?
- Connection kết thúc bằng QUIT/FIN hay RST?

---

## 6. Part 1B – Capture Project 01 trên hai máy

### 6.1 Kiến trúc thực tế của Project 01

Project hiện tại là Hybrid FTP:

- Control channel: TCP port `2121`.
- Data channel: UDP + giao thức RDT tự cài đặt.
- Server bind control tại `0.0.0.0:2121`.
- Tài khoản lab: `admin / 123456`.
- Server root thực tế: thư mục `data/server_storage/`.
- Client download vào `data/client_downloads/`.
- Active Mode dùng lệnh `PORT <udp-port>`.
- Passive Mode dùng `PASV`, server trả `UDP_PORT=<port>`.
- Passive handshake retry tối đa 5 lần nếu SYN probe hoặc SYN-ACK bị mất trên Wi-Fi.
- RDT dùng sequence number, cumulative ACK, checksum, timeout, retransmission, sliding window và FIN handshake.

Server và client dùng hai vùng lưu trữ riêng. Lệnh `STOR active_test.bin` lưu file remote thành `data/server_storage/active_test.bin`; file local của client nằm trong `data/client_downloads/`.

### 6.2 Yêu cầu hai máy

Đề yêu cầu client và server chạy trên hai máy khác nhau trong cùng LAN.

Ví dụ:

```text
Server PC: 192.168.1.10
Client PC: 192.168.1.20
```

Trên mỗi máy chạy:

```powershell
ipconfig
```

Ghi IPv4 thực tế vào `network_info.txt`.

Không kết nối bằng `localhost` hoặc `127.0.0.1`. Nếu chạy cùng máy, Wireshark phải capture Npcap Loopback Adapter và không chứng minh đúng yêu cầu hai PC của đề.

### 6.3 Firewall

Trên server, mở PowerShell bằng quyền Administrator:

```powershell
New-NetFirewallRule -DisplayName "Hybrid FTP TCP 2121" -Direction Inbound -Protocol TCP -LocalPort 2121 -Action Allow
New-NetFirewallRule -DisplayName "Hybrid FTP UDP" -Direction Inbound -Protocol UDP -Action Allow
```

Trên client, Active Mode cần nhận UDP inbound:

```powershell
New-NetFirewallRule -DisplayName "Hybrid FTP UDP" -Direction Inbound -Protocol UDP -Action Allow
```

Chỉ thực hiện trong mạng Private/LAN tin cậy. Dự án dùng UDP port động và chưa có NAT traversal, vì vậy không phù hợp để chạy trực tiếp giữa hai mạng Internet/NAT khác nhau nếu chưa cấu hình thêm.

### 6.4 Tạo dữ liệu test

Trên client, từ thư mục gốc project, tạo hai file nhị phân 20 KB:

```powershell
$payload = [byte[]]::new(20480)
for ($i = 0; $i -lt $payload.Length; $i++) {
    $payload[$i] = [byte]($i % 251)
}
[IO.File]::WriteAllBytes(
    (Join-Path (Get-Location) "data\client_downloads\active_test.bin"),
    $payload
)
Copy-Item "data\client_downloads\active_test.bin" `
          "data\client_downloads\passive_test.bin"
```

File 20 KB tạo khoảng 20 DATA packet vì mỗi payload tối đa 1024 byte. Số lượng này đủ để quan sát sliding window 8 packet và ACK.

Lấy SHA-256 trước khi truyền:

```powershell
Get-FileHash data\client_downloads\active_test.bin -Algorithm SHA256
Get-FileHash data\client_downloads\passive_test.bin -Algorithm SHA256
```

Lưu kết quả vào `hashes.txt`.

### 6.5 Chạy server

Trên máy server, tại thư mục gốc repository:

```powershell
python -m server.main_server
```

Nếu máy dùng Python Launcher:

```powershell
py -3 -m server.main_server
```

Terminal server cần hiển thị:

```text
Starting Hybrid FTP Server on 0.0.0.0:2121...
Server root directory: ...\data\server_storage
```

### 6.6 Capture Active Mode

Trên máy client:

1. Mở Wireshark và chọn Wi-Fi/Ethernet.
2. Có thể đặt capture filter, thay IP ví dụ bằng server IP thực tế:

   ```text
   host 192.168.1.10 and (tcp port 2121 or udp)
   ```

3. Bắt đầu capture.
4. Chạy client:

   ```powershell
   python -m client.main_client --host 192.168.1.10 --port 2121
   ```

5. Nhập các lệnh:

   ```text
   USER admin
   PASS 123456
   TYPE I
   MODE S

   PORT 50001
   LIST

   PORT 50001
   STOR active_test.bin

   HASH active_test.bin
   ```

6. Sau khi upload hoàn tất, ở terminal khác trên client đổi tên bản gốc:

   ```powershell
   Move-Item data\client_downloads\active_test.bin `
             data\client_downloads\active_test.sent.bin
   ```

7. Quay lại cửa sổ client và nhập:

   ```text
   PORT 50001
   RETR active_test.bin
   HASH active_test.bin
   QUIT
   ```

   Client hiện tại tự gửi `HASH` sau `RETR` để so sánh hash local/server; lệnh `HASH` nhập thêm vẫn có thể dùng làm bằng chứng control channel.

8. Đổi tên file vừa tải xuống:

   ```powershell
   Move-Item data\client_downloads\active_test.bin `
             data\client_downloads\active_test.downloaded.bin
   ```

9. Dừng capture và lưu:

   ```text
   part1_project01_active.pcapng
   ```

Không nhập `STOR data\client_downloads\active_test.bin`. Client gửi nguyên argument làm remote path. Chỉ nhập `STOR active_test.bin` để client tự tìm file trong `data/client_downloads/` và server lưu đúng tên ở server root.

### 6.7 Capture Passive Mode

Bắt đầu một capture mới và chạy một client session mới:

```text
USER admin
PASS 123456
TYPE I
MODE S

PASV
LIST

PASV
STOR passive_test.bin

HASH passive_test.bin
```

Sau khi upload, đổi tên bản gốc:

```powershell
Move-Item data\client_downloads\passive_test.bin `
          data\client_downloads\passive_test.sent.bin
```

Tiếp tục trong client:

```text
PASV
RETR passive_test.bin
HASH passive_test.bin
QUIT
```

Đổi tên file tải xuống:

```powershell
Move-Item data\client_downloads\passive_test.bin `
          data\client_downloads\passive_test.downloaded.bin
```

Dừng và lưu:

```text
part1_project01_passive.pcapng
```

Nên gửi `PASV` trước mỗi `LIST`, `STOR` và `RETR` để mỗi transfer có một UDP port rõ ràng, dễ đối chiếu trong capture.

### 6.8 Kiểm tra hash sau transfer

```powershell
Get-FileHash data\client_downloads\*.sent.bin -Algorithm SHA256
Get-FileHash data\client_downloads\*.downloaded.bin -Algorithm SHA256
```

Hai hash tương ứng phải giống nhau. Ghi kết quả vào `hashes.txt` và chụp terminal làm bằng chứng bổ sung.

### 6.9 Display filter cho Project 01

Thay IP bằng server IP thực tế:

```wireshark
ip.addr == 192.168.1.10 && (tcp.port == 2121 || udp)
```

Chỉ xem control channel:

```wireshark
tcp.port == 2121
```

Tìm control handshake:

```wireshark
tcp.port == 2121 && tcp.flags.syn == 1
```

Active data port cố định trong kịch bản:

```wireshark
udp.port == 50001
```

Với Passive Mode, lấy port từ reply:

```text
227 ... UDP_PORT=<passive_port>
```

Sau đó lọc:

```wireshark
udp.port == <passive_port>
```

### 6.10 Header RDT tự xây dựng

Header RDT dài 13 byte và dùng big-endian/network byte order:

| Offset trong UDP payload | Field | Kích thước |
|---:|---|---:|
| 0–3 | Sequence number | 4 byte |
| 4–7 | Acknowledgment number | 4 byte |
| 8–9 | Checksum | 2 byte |
| 10–11 | Payload length | 2 byte |
| 12 | Flags | 1 byte |
| 13 trở đi | Payload | Tối đa 1024 byte |

Các flag:

| Giá trị | Ý nghĩa |
|---:|---|
| `0x01` | SYN |
| `0x02` | ACK |
| `0x03` | SYN + ACK |
| `0x04` | FIN |
| `0x08` | DATA |

Filter theo byte flags:

```wireshark
udp.payload[12] == 0x01
```

```wireshark
udp.payload[12] == 0x02
```

```wireshark
udp.payload[12] == 0x03
```

```wireshark
udp.payload[12] == 0x04
```

```wireshark
udp.payload[12] == 0x08
```

Wireshark không có dissector riêng cho RDT của project nên các field được đọc từ phần `Data`/hex của UDP payload. Khi chụp ảnh, đánh dấu đúng byte offset và giải thích cách đổi byte sang số.

### 6.11 Cơ chế RDT cần biết để phân tích

- Payload tối đa: 1024 byte.
- Header: 13 byte.
- Sliding window cố định: 8 packet.
- Cumulative ACK.
- Retransmission timeout: 0,3 giây.
- Fast retransmit sau 3 duplicate ACK.
- DATA retry tối đa 10 lần khi cumulative ACK không tiến triển; bộ đếm reset khi ACK hợp lệ làm cửa sổ trượt lên.
- Receiver dừng sau 10 RTO liên tiếp không nhận DATA hợp lệ thay vì chờ vô hạn.
- Internet checksum 16-bit.
- DATA dùng sequence number `0, 1, 2, ...`.
- ACK number biểu diễn sequence tiếp theo receiver mong đợi.
- FIN được thử tối đa 10 lần; transfer lỗi trả về control channel thay vì lặp vô hạn.

Ví dụ: receiver nhận đúng DATA sequence `0`, ACK trả về thường có `ack = 1`, nghĩa là đã nhận đến sequence 0 và đang chờ sequence 1.

### 6.12 Checklist ảnh Project 01

#### O1 – Hai máy và IP

Chụp `ipconfig` client/server và terminal server nhận connection. Ảnh phải chứng minh hai địa chỉ IP khác nhau.

#### O2 – TCP control handshake

Filter:

```wireshark
tcp.port == 2121 && tcp.flags.syn == 1
```

Khoanh IP, source/destination port và SYN/SYN-ACK.

#### O3 – Credential cleartext

Follow TCP Stream của port 2121 và khoanh:

```text
USER admin
PASS 123456
230 ...
```

#### O4 – Active Mode

Khoanh lệnh `PORT 50001` và reply chấp nhận. Sau đó chỉ ra packet UDP đầu tiên từ server tới client port `50001`.

#### O5 – Active upload handshake

Khoanh theo thứ tự:

- Server → client: flags `0x01` SYN.
- Client → server: flags `0x03` SYN+ACK.
- Client → server: flags `0x08` DATA.

#### O6 – Passive Mode

Khoanh:

```text
PASV
227 ... UDP_PORT=<port>
```

Sau đó chỉ ra client chủ động gửi UDP tới port này. Với LIST/RETR passive, client gửi SYN probe để server biết endpoint UDP của client.

#### O7 – DATA packet

Khoanh/giải mã:

- Sequence number ở byte 0–3.
- Payload length ở byte 10–11.
- Flags ở byte 12 là `0x08`.
- Payload bắt đầu từ byte 13.

#### O8 – Cumulative ACK

Chụp ACK packet, giải mã:

- Acknowledgment number ở byte 4–7.
- Flags ở byte 12 là `0x02`.
- Nêu ACK này xác nhận đến DATA sequence nào.

#### O9 – FIN

Chụp packet có flags `0x04`, chỉ ra sequence/ack liên quan và chiều gửi.

#### O10 – Transfer reply và hash

Khoanh các reply `150`/`125`, `226`, lệnh `HASH`, SHA-256 và terminal báo hash giống nhau.

#### O11 – Listing/upload/download

Có ít nhất một ảnh cho từng hoạt động:

- `LIST` và listing data.
- `STOR` và DATA/ACK.
- `RETR` và DATA/ACK.

#### O12 – Statistics/Conversations

Mở `Statistics → Conversations` hoặc `Statistics → Endpoints`, ghi packet/byte count của hai session Active/Passive để hỗ trợ phần so sánh.

### 6.13 So sánh Active Mode và Passive Mode

| Nội dung | Active Mode | Passive Mode |
|---|---|---|
| Control TCP | Client → server port `2121` | Client → server port `2121` |
| Lệnh thiết lập | `PORT 50001` | `PASV` |
| Bên mở UDP port nhận data | Client | Server |
| Bên chủ động liên hệ UDP | Server liên hệ client | Client liên hệ server |
| Firewall | Client cần nhận UDP inbound | Server cần nhận UDP inbound |
| NAT | Thường khó hơn | Thường thuận lợi hơn |
| Data protocol trong project | UDP + RDT | UDP + RDT |

Chi tiết theo implementation hiện tại:

- Active download/LIST: server tạo UDP socket động và gửi data tới UDP port client đã đăng ký.
- Active upload: server gửi SYN từ UDP port động tới client port; client trả SYN+ACK rồi upload tới endpoint đó.
- Passive download/LIST: server mở UDP port, client gửi SYN probe tới server rồi nhận data.
- Passive upload: client gửi data tới UDP port server trả trong `227`.

### 6.14 Phân tích bảo mật Project 01

- TCP control channel không dùng TLS.
- `USER`, `PASS`, command và reply đều có thể đọc trong Follow TCP Stream.
- UDP/RDT có checksum nhưng checksum chỉ phát hiện lỗi bit, không mã hóa dữ liệu.
- Người capture được traffic có thể đọc credential, filename, command và nội dung không mã hóa.
- Không dùng password thật trong thí nghiệm; chỉ dùng tài khoản lab.
- Để bảo mật thực tế cần TLS/FTPS, SSH/SFTP hoặc mã hóa/xác thực ở tầng ứng dụng.

---

# PART 2 – HTTP PROTOCOL ANALYSIS

## 7. Viết raw HTTP socket client

Tạo `source/http_client.py` với nội dung:

```python
import socket

host = "www.google.com"
port = 80

request = (
    "GET / HTTP/1.1\r\n"
    "Host: www.google.com\r\n"
    "User-Agent: SocketLab/1.0\r\n"
    "Connection: close\r\n"
    "\r\n"
)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.connect((host, port))
    sock.sendall(request.encode("ascii"))

    response = bytearray()
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response.extend(chunk)

print(response.decode("utf-8", errors="replace"))
```

Yêu cầu quan trọng:

- Phải dùng raw TCP socket, không dùng `requests`, `urllib`, browser hoặc HTTP library.
- Phải gửi request tự tạo.
- Dòng và header kết thúc bằng CRLF `\r\n`.
- Sau header cuối phải có thêm một dòng trống `\r\n`.
- Dùng `AF_INET` để thí nghiệm này dùng IPv4 rõ ràng.
- `Connection: close` giúp client biết response kết thúc khi server đóng connection nếu không dựa vào cách khác.

---

## 8. Capture DNS và HTTP

### 8.1 Chuẩn bị

1. Đóng trình duyệt và ứng dụng tạo traffic không cần thiết.
2. Nếu có quyền Administrator, xóa DNS cache:

   ```powershell
   ipconfig /flushdns
   ```

3. Mở Wireshark và chọn đúng interface Internet.
4. Bắt đầu capture trước khi chạy chương trình.

Nếu DNS đã được cache và capture không có DNS query, dừng, xóa DNS cache rồi capture lại. Không nên tự tạo DNS packet tách rời mà không giải thích.

### 8.2 Chạy client

```powershell
python source\http_client.py
```

Hoặc:

```powershell
py -3 source\http_client.py
```

Chờ chương trình in hết response và kết thúc. Sau đó dừng capture và lưu:

```text
lab_capture.pcapng
```

### 8.3 Display filter HTTP

Xem DNS và TCP port 80:

```wireshark
dns || tcp.port == 80
```

Chỉ HTTP:

```wireshark
http
```

Chỉ request:

```wireshark
http.request
```

Chỉ response:

```wireshark
http.response
```

Handshake:

```wireshark
tcp.flags.syn == 1
```

Đóng connection:

```wireshark
tcp.flags.fin == 1 || tcp.flags.reset == 1
```

Sau khi xác định Google IP:

```wireshark
ip.addr == <google_ip> && tcp.port == 80
```

Sau khi xác định TCP stream number:

```wireshark
tcp.stream eq <stream_number>
```

Nếu Wireshark không nhận HTTP trên port 80, chọn packet → `Analyze → Decode As → HTTP`.

---

## 9. Follow TCP Stream và reassembly

Chọn packet của HTTP connection:

```text
Right-click → Follow → TCP Stream
```

Request phải có dạng:

```http
GET / HTTP/1.1
Host: www.google.com
User-Agent: SocketLab/1.0
Connection: close
```

Status thực tế có thể là `200 OK`, `301 Moved Permanently` hoặc một response khác. Báo cáo phải dùng status và header trong capture thực tế, không giả định trước.

Để xem reassembly:

1. Chọn packet cuối nơi Wireshark hiển thị HTTP response hoàn chỉnh.
2. Mở TCP trong Packet Details.
3. Mở cây có dạng `[N Reassembled TCP Segments]`.
4. Ghi các packet cấu thành và độ dài từng segment.

Nếu cần so sánh raw segment với reassembled response, kiểm tra:

```text
Edit → Preferences → Protocols → TCP
→ Allow subdissector to reassemble TCP streams
```

---

## 10. Checklist ảnh Part 2

### H1 – DNS query và response

Filter:

```wireshark
dns
```

Khoanh:

- Query name `www.google.com`.
- A record/IPv4 response.
- Packet number query và response.

### H2 – TCP three-way handshake

Khoanh ba packet:

- SYN.
- SYN/ACK.
- ACK.

Ghi client/server IP, client ephemeral port, server port 80, sequence và acknowledgment number.

### H3 – TCP options

Trong SYN và SYN/ACK mở `Transmission Control Protocol → Options`, khoanh:

- Maximum Segment Size (MSS).
- Window Size Value.
- Window Scale nếu có.
- Calculated Window Size nếu Wireshark hiển thị.

### H4 – HTTP request

Khoanh:

- `GET / HTTP/1.1`.
- `Host`.
- `User-Agent`.
- `Connection: close`.
- Packet number chứa request.

### H5 – HTTP response

Khoanh các field thực tế:

- Status code và reason phrase.
- `Content-Type`.
- `Content-Length` nếu có.
- `Transfer-Encoding` nếu có.
- `Location` nếu redirect.
- `Connection`.
- `Date` nếu đề hỏi.

### H6 – Follow TCP Stream

Chụp request và response ở dạng text. Đảm bảo thấy rõ client/server direction bằng màu của Follow Stream.

### H7 – Reassembled TCP Segments

Mở cây `[N Reassembled TCP Segments]`, chụp danh sách segment và packet chứa response hoàn chỉnh.

### H8 – Ba TCP data segment liên tiếp

Chọn ba packet server → client và lập bảng:

| Packet | Seq | TCP Len | Next Seq | Ack |
|---:|---:|---:|---:|---:|
| ... | ... | ... | ... | ... |

Với relative sequence number và data packet bình thường:

```text
Next Seq = Seq + TCP Len
```

SYN và FIN tiêu thụ thêm một sequence number nên phải lưu ý khi áp dụng công thức cho các packet đó.

### H9 – Connection teardown

Filter:

```wireshark
tcp.flags.fin == 1 || tcp.flags.reset == 1
```

Khoanh:

- Bên gửi FIN/RST đầu tiên.
- Packet number.
- Seq/Ack.
- Packet ACK cuối.

### H10 – Tổng byte

Dùng `Statistics → Conversations → TCP` hoặc cộng `tcp.len` theo từng chiều.

Phải phân biệt:

- TCP payload client gửi.
- TCP payload server gửi.
- HTTP header bytes.
- HTTP body bytes.
- Tổng frame bytes gồm Ethernet/IP/TCP header.

Không so sánh `Content-Length` trực tiếp với tổng frame bytes. `Content-Length` chỉ mô tả body; nếu response dùng chunked thì body trên wire còn có chunk-size marker và CRLF.

---

## 11. Worksheet trả lời câu hỏi Part 2

Số thứ tự dưới đây dùng làm checklist. Khi viết báo cáo, giữ số câu đúng như đề gốc.

### A. Name Resolution & Addressing

- DNS query có xảy ra trước TCP connection không?
- Hostname nào được query?
- DNS trả về IP nào?
- Client thực sự kết nối tới IP nào?
- Client dùng IPv4 hay IPv6?
- Client source IP là gì?
- Client source TCP port là gì?
- Server TCP port là gì?
- Packet SYN, SYN/ACK và ACK là những packet nào?
- RTT từ SYN đến SYN/ACK là bao nhiêu?
- MSS và initial advertised window của hai bên là bao nhiêu?
- MSS/window của hai phía giống hay khác, và điều đó có ý nghĩa gì?

### B. HTTP Request

- Packet nào chứa HTTP request?
- Request line chính xác là gì?
- HTTP method là gì?
- Destination IP là gì?
- HTTP version là gì?
- Liệt kê toàn bộ request header.
- `Host` header có giá trị gì?
- Vì sao `Host` cần thiết trong HTTP/1.1?
- Tổng số byte request client gửi khoảng bao nhiêu?

### C. HTTP Response

- Status code và reason phrase là gì?
- Server có redirect không?
- Nếu redirect, `Location` trỏ tới URL nào?
- Liệt kê các response header quan trọng.
- `Content-Type` là gì?
- Có `Content-Length` không? Nếu có, giá trị bao nhiêu?
- Có `Transfer-Encoding: chunked` không?
- Response body kết thúc bằng Content-Length, chunk cuối hay connection close?
- Vì sao chương trình biết đã đọc hết response?

### D. TCP Segmentation & Reassembly

- Server response được chia thành bao nhiêu TCP packet/segment?
- Packet nào hiển thị HTTP response đã reassemble?
- Cây `[N Reassembled TCP Segments]` liệt kê những packet nào?
- Vì sao Wireshark đọc được response hoàn chỉnh dù data đến qua nhiều segment?
- Chọn ba data segment liên tiếp và ghi Seq/TCP Len/Next Seq/Ack.
- Chứng minh sequence number sau bằng sequence trước cộng payload length.
- ACK xuất hiện riêng hay được piggyback cùng data?
- Total bytes client gửi và server gửi là bao nhiêu?
- Tổng TCP payload response khác HTTP body length như thế nào?
- Nếu chunked, chunk-size marker ảnh hưởng tổng byte trên wire ra sao?

### E. Closing the Connection

- Bên nào gửi FIN hoặc RST đầu tiên?
- Connection kết thúc bằng FIN handshake hay RST?
- Các packet teardown là packet nào?
- Sequence/Acknowledgment number cuối có hợp lý không?
- `Connection: close` liên hệ với teardown như thế nào?

### F. Security Reflection và lifecycle

- Người nghe lén có thể đọc request/response HTTP port 80 không?
- Nếu đổi sang HTTPS port 443 thì phần nào sẽ được mã hóa?
- Viết một đoạn ngắn mô tả toàn bộ vòng đời:

  ```text
  DNS → SYN/SYN-ACK/ACK → HTTP GET → HTTP response
      → TCP segmentation/reassembly → FIN/ACK
  ```

---

## 12. Mẫu cách trả lời câu hỏi

### Mẫu trả lời ngắn

> **Câu X – Server dùng cổng nào?**  
> Server dùng TCP port `80`. Packet `No. 17` là SYN/ACK từ server; trong TCP header, `Source Port = 80`. Xem Hình H2-02.

### Mẫu trả lời có tính toán

> **Câu Y – Kiểm tra sequence number của ba segment liên tiếp.**  
> Packet 45 có `Seq = 1`, `TCP Len = 1460`, nên `Next Seq = 1461`. Packet 46 bắt đầu tại `Seq = 1461`. Tương tự, packet 46 có `TCP Len = 1460`, nên packet tiếp theo bắt đầu tại `Seq = 2921`. Kết quả phù hợp với cơ chế đánh số theo byte của TCP. Xem Hình H8-01.

Các con số trên chỉ minh họa cách trình bày; phải thay bằng số trong capture của nhóm.

### Mẫu phân tích bảo mật

> Trong Follow TCP Stream, packet ... hiển thị trực tiếp `USER ...` và `PASS ...`. Điều này chứng minh control channel không được mã hóa. Người có khả năng nghe lén cùng mạng có thể lấy credential và tái sử dụng tài khoản. Checksum của RDT chỉ phát hiện lỗi dữ liệu, không bảo vệ tính bí mật.

---

## 13. Bố cục báo cáo đề xuất

### 13.1 Part 1 – FTP, khoảng 8–12 trang theo yêu cầu đề

1. Mục tiêu.
2. Mô hình/topology và địa chỉ IP.
3. Công cụ, phiên bản và dữ liệu test.
4. FTP công cộng – connection/authentication.
5. FTP công cộng – listing/upload/download.
6. Project 01 – kiến trúc TCP control/UDP data.
7. Project 01 – Active Mode.
8. Project 01 – Passive Mode.
9. So sánh Active/Passive.
10. Kiểm tra hash và độ tin cậy RDT.
11. Phân tích cleartext credential/bảo mật.
12. Trả lời các câu hỏi và kết luận Part 1.

### 13.2 Part 2 – HTTP

1. Mục tiêu và source code raw socket.
2. DNS resolution.
3. TCP three-way handshake.
4. TCP options, MSS, window và RTT.
5. HTTP request.
6. HTTP response.
7. Segmentation và reassembly.
8. Sequence/ACK/byte totals.
9. Connection teardown.
10. HTTP so với HTTPS.
11. Trả lời câu hỏi 1–24.
12. Lifecycle và kết luận.

Có thể đặt câu trả lời ngay sau từng phần phân tích thay vì gom toàn bộ xuống cuối, miễn giữ số câu rõ ràng và không bỏ sót.

---

## 14. Danh sách file cần kiểm tra trước khi nộp

### Capture/network files

- [ ] `part1_public_ftp.pcapng`.
- [ ] `part1_project01_active.pcapng`.
- [ ] `part1_project01_passive.pcapng`.
- [ ] `lab_capture.pcapng`.
- [ ] Tất cả `.pcapng` mở lại được và không rỗng.

### Source files

- [ ] `http_client.py` là code tự viết bằng raw socket.
- [ ] Source Project 01 nếu giảng viên/LMS yêu cầu đính kèm lại.

### Data files

- [ ] Ảnh dùng cho FTP công cộng.
- [ ] File upload/download Active Mode.
- [ ] File upload/download Passive Mode.
- [ ] `hashes.txt` chứng minh file trước/sau giống nhau.
- [ ] `network_info.txt` ghi IP/port/stream thực tế.

### Report

- [ ] Một report PDF có cấu trúc rõ ràng.
- [ ] Part 1 đáp ứng yêu cầu độ dài của đề.
- [ ] Mỗi câu hỏi đã có câu trả lời.
- [ ] Câu trả lời có packet number và field/value.
- [ ] Mỗi ảnh có mã hình và caption.
- [ ] Field/value quan trọng đã được khoanh/highlight.
- [ ] Có phân tích Active/Passive.
- [ ] Có phân tích credential cleartext.
- [ ] Có DNS, TCP handshake, HTTP request/response, reassembly và teardown.
- [ ] Có câu lifecycle cuối cùng.

---

## 15. Các lỗi thường làm mất điểm

- Capture bắt đầu sau khi connection đã mở nên mất DNS hoặc TCP handshake.
- Chạy Project 01 bằng `localhost` thay vì hai máy.
- Chỉ nộp screenshot mà không nộp `.pcapng`.
- Screenshot không thấy packet number hoặc display filter.
- Không khoanh field/value trả lời câu hỏi.
- Dùng FTPS/SFTP nên không thấy FTP cleartext.
- Dùng `requests` thay vì raw socket cho Part 2.
- Request thiếu CRLF hoặc dòng trống cuối header.
- Chỉ chụp Follow TCP Stream nhưng không chỉ ra packet gốc.
- Nhầm `Content-Length` với tổng Ethernet/frame bytes.
- Không phân biệt control channel TCP với data channel.
- Không xác định passive UDP port từ reply `227`.
- Gọi checksum là encryption.
- Chỉ chạy Active hoặc chỉ chạy Passive.
- Trả lời một phần danh sách câu hỏi và bỏ các câu tưởng là trùng nhau.
- Dùng số packet/IP/port ví dụ thay cho capture thực tế.

---

## 16. Kết luận ngắn

Để hoàn thành đầy đủ Project 2, cần thực hiện bốn lượt capture, lưu đầy đủ file `.pcapng`, chuẩn bị dữ liệu upload/download và hash, chụp ảnh có đánh dấu field/value, đồng thời trả lời toàn bộ câu hỏi trong đề. Các giá trị như port cố định của project, cấu trúc RDT và tài khoản lab có thể lấy từ source code; các giá trị IP, port động, packet number, RTT, MSS, window, status code và byte count phải lấy từ capture thực tế của nhóm.
