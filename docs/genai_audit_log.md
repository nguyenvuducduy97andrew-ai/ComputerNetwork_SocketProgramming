# Nhật ký sử dụng GenAI

Tài liệu này tổng hợp các prompt người dùng đã gửi trong phiên làm việc nhằm phục vụ việc theo dõi quá trình kiểm tra, sửa lỗi, refactor và cập nhật tài liệu cho dự án Hybrid FTP.

## Các prompt theo thứ tự thời gian

### Prompt 1 — Kiểm tra server handler và Client Session

> Đây là một mô hình Client-Server Hybrid FTP với TCP cho việc kết nối, gửi, trả các lệnh và phản hồi giữa Client và Server. Trong server/ hãy kiểm tra logic và xác định lỗi/thiếu sót/dư thừa (nếu có tồn tại) của các lệnh handler. Sau đó kiểm tra các trường của Client Session nhằm đáp ứng được các lệnh đã được liệt kê trong command_handler.py.

### Prompt 2 — Kiểm tra lỗi 1.1–1.4

> 1.4. Giao thức PASV giữa client và server không khớp.
>
> Tui cần hướng để sửa lỗi này, các lỗi ở phía trước tui đã chỉnh, hãy kiểm tra lại các lỗi 1.1, 1.2 và 1.3 xem cách tui sửa có đúng chưa.

### Prompt 3 — Socket active UDP dư thừa

Ngữ cảnh được chọn từ phản hồi trước:

> Có một vấn đề phụ chưa liên quan trực tiếp tới lỗi import: `active_udp_socket` được tạo trong `handle_port()`, nhưng `send_file()` lại tạo socket active mới. Socket trong session hiện dư thừa và chưa được đóng đúng cách.

Yêu cầu:

> Đề xuất cách sửa lỗi này.

### Prompt 4 — Áp dụng sửa lỗi active UDP

> Hãy áp dụng cách sửa này tui cho bạn quyền thay đổi code base dựa theo đề xuất trên.

### Prompt 5 — Lỗi 1.5 về passive UDP

> Hãy đề xuất hướng sửa lỗi 1.5 `passive_udp_address` đang mang sai ý nghĩa.

### Prompt 6 — Kiểm tra lại flow passive UDP

> Tui vừa sửa, hãy kiểm tra flow này đã được fix hoàn chỉnh chưa.

### Prompt 7 — Lỗi 1.6 liên quan APPE

> Hãy address lỗi 1.6 liên quan tới APPE.

### Prompt 8 — Kiểm tra lỗi 2.1 và đề xuất sửa 2.2

> Kiểm tra tui đã sửa lỗi 2.1 chưa. Lỗi 2.2 cần sửa như nào?

### Prompt 9 — Kiểm tra lỗi 2.3

> Kiểm tra lại lỗi 2.3.

### Prompt 10 — Metadata cho LIST

> Cách thêm metadata cho List.

### Prompt 11 — Truyền LIST qua data channel

> Hãy sửa lại theo hướng gửi listing qua data channel.

### Prompt 12 — Ctrl+C không shutdown server

> Kiểm tra behavior bên trong vòng lặp của main server. Khi tui start một server thì không dùng Ctrl+C để shutdown được.

### Prompt 13 — Rà soát reply và log phía server

> Hãy duyệt qua server/ để kiểm tra các behavior reply lệnh, ghi log và note lại những thứ cần sửa.

### Prompt 14 — Refactor handler trả nhiều reply

> Hãy đưa ra đề xuất refactor lại handler để trả về được nhiều hơn 1 reply.

### Prompt 15 — Kiểm tra và cài đặt phương án multi-reply

> Hãy kiểm tra lại phương án trên và bắt đầu cài đặt.

### Prompt 16 — Tích hợp progress monitor

> Hãy ráp `cli_monitor` vào để thể hiện tiến trình truyền/nhận file bên client.

### Prompt 17 — Thống nhất reply và bổ sung 503

> Hãy sửa lại để nhất quán các reply, tui có thêm reply 503 rồi.

### Prompt 18 — Rà soát client handler và tính độc lập

> Hãy kiểm tra các hàm handle lệnh của client để loại bỏ những trường dữ liệu thừa trong hàm và kiểm tra tính đúng đắn của phía client. Đảm bảo 2 bên server và client có thể hoạt động độc lập.

### Prompt 19 — Theo dõi lỗi HELP chỉ trả một dòng

> Track theo lệnh Help từ client, nó chỉ trả về 1 dòng `214 Available commands`.

### Prompt 20 — Yêu cầu hướng dẫn tự sửa HELP

> Cho tui hướng dẫn sửa, tui sẽ tự làm.

### Prompt 21 — Kiểm tra bước sửa HELP phía client

> Hãy kiểm tra lại bước sửa handler HELP phía client.

### Prompt 22 — Yêu cầu server `handle_help` hoàn chỉnh

> Vậy cho tui `server/handle_help` hoàn chỉnh mới đi.

### Prompt 23 — Cập nhật tài liệu kiến trúc

> Cập nhật ARCHITECTURE và README để phản ánh được chính xác cấu trúc project hiện giờ.

### Prompt 24 — Tổng hợp prompt vào tài liệu GenAI

> Tổng hợp các prompt của tui trong session này bỏ vào `gen_ai_` trong doc.

### Prompt 25 — Rà soát logical flow toàn bộ server

> Kiểm tra mô hình Hybrid FTP dùng TCP control và UDP/RDT data, trace tuần tự từng server handler và xác định các handler hoặc logic chung còn có vấn đề; chưa tập trung vào client.

### Prompt 26 — Chuyển upload handler sang transfer worker

> Sửa `handle_stor`, `handle_stou` và `handle_appe` tương tự `handle_retr`: đặt `receive_file()` trong closure `_worker`, không yield thêm reply sau khi khởi động worker và để worker tự gửi reply cuối `226`/`426` qua control connection.

### Prompt 27 — Làm rõ command policy trong lúc transfer

> Xác nhận ý nghĩa của policy command khi transfer đang chạy và việc chỉ cho phép `ABOR`, `NOOP`, `STAT`, `QUIT` có ngăn hai transfer chạy song song trong cùng một session hay không.

### Prompt 28 — Làm rõ mô hình concurrency

> Xác nhận server hiện hỗ trợ multi-thread để phục vụ nhiều client/transfer nhưng không sử dụng multi-process.

### Prompt 29 — Đánh giá dự án theo requirements

> Đọc `requirements.txt`, đánh giá cấu trúc và mức độ hiện tại của dự án theo các tiêu chí cơ bản, nâng cao và xuất sắc.

### Prompt 30 — Lập kế hoạch Active Upload

> Lên kế hoạch hiện thực Active Upload dựa trên cấu trúc server và data-channel setup hiện có.

### Prompt 31 — Sửa cancellation trong RDT

> Bổ sung khả năng hủy RDT và kiểm tra vai trò hiện tại của progress callback trước khi quyết định truyền `cancel_event` vào `send`/`receive`.

### Prompt 32 — Tiếp tục triển khai Active Upload

> Tiếp tục từ bước đã tạm dừng để kiểm tra progress callback; triển khai `expected_peer`, active receive socket phía server và handshake `SYN`/`SYN-ACK`, đồng thời lưu ý mọi thay đổi trong `shared/`.

### Prompt 33 — Hoàn thiện Active Upload phía client và cleanup

> Mở Active Upload phía client, bổ sung cleanup socket/session và ưu tiên tái sử dụng helper hiện có thay vì cleanup thủ công từng trường.

### Prompt 34 — Thiết kế trường data socket hiện hành

> Đánh giá nên dùng `active_data_socket` hay một `current_data_socket` chung cho cả active và passive mode, sau đó triển khai quy trình cleanup đã thống nhất.

### Prompt 35 — Đánh giá lại mức độ hoàn thiện

> Sau các thay đổi Active Upload, cancellation và cleanup, đánh giá lại hệ thống đã đạt mức nào trong các tiêu chí của `requirements.txt`.

### Prompt 36 — Xác định duplicate reply của ABOR

> Trace vị trí khiến `ABOR` phát hai reply và phân tích ưu, nhược điểm của các phương án phân quyền reply giữa control handler và transfer worker.

### Prompt 37 — Chạy server và client tương tác

> Khởi động server ở cổng mặc định trong cửa sổ hiển thị, sau đó mở một cửa sổ khác chạy client để kiểm tra tương tác trực tiếp.

### Prompt 38 — Làm rõ đường dẫn ảo của PWD

> Đánh giá việc `PWD` trả `/` thay vì `data/` và làm rõ quan hệ giữa server root vật lý với filesystem ảo mà client nhìn thấy.

### Prompt 39 — Kiểm tra khả năng chạy trên hai máy

> Xác định hệ thống có chạy được khi client và server ở hai máy khác nhau hay không, bao gồm IP LAN, TCP `2121`, UDP Active/Passive, firewall và hạn chế NAT.

### Prompt 40 — Cập nhật README và ARCHITECTURE

> Ghi hướng dẫn triển khai hai máy vào README; đồng thời cập nhật README theo hướng dẫn sử dụng và ARCHITECTURE theo trạng thái kỹ thuật hiện tại của project.

### Prompt 41 — Hướng dẫn hoàn thiện SHA-256 tự động

> Đề xuất workflow để client tự động so sánh SHA-256 trước và sau `RETR`, `STOR`, `STOU`, `APPE`, bao gồm trường hợp `TYPE A`, tên file tự sinh và append.

### Prompt 42 — Đóng gói integration test

> Chuyển các flow Active Upload, lọc UDP peer và cleanup/cancellation thành test suite tự động trong thư mục `tests/`.

### Prompt 43 — Cho phép chạy từng test trực tiếp

> Điều chỉnh ba test mới để có thể chạy riêng bằng cú pháp `python tests/<tên_file>.py`, giống hai test cũ.

### Prompt 44 — Cập nhật cú pháp kiểm thử trong README

> Sửa phần kiểm thử trong README để mỗi test có một lệnh chạy riêng, không gom ba test mới vào cùng một command.

### Prompt 45 — Cập nhật GenAI audit log

> Tổng hợp các prompt của người dùng và bổ sung vào `docs/genai_audit_log.md`.

### Prompt 46 — Rà soát flow và defect phía client

> Hãy kiểm tra `client/` và xác định flow hoạt động hiện tại của client, note lại nếu có defect trong client.

### Prompt 47 — Lập kế hoạch xử lý defect ABOR

Ngữ cảnh được chọn từ phản hồi trước:

> Cao — `ABOR` thực tế không thể hủy transfer đang chạy.

Yêu cầu:

> Hãy đưa ra plan để giải quyết từng vấn đề một, bắt đầu với defect này.

### Prompt 48 — Giới hạn giải pháp theo requirements

> Hãy giới hạn ở mức độ được nêu ra trong file `requirements.txt`.

### Prompt 49 — Cập nhật GenAI audit log với các prompt mới

> Tổng hợp prompt của tui để bỏ vào file `genai_audit`.

## Phạm vi công việc trong phiên

Các prompt trên tập trung vào:

- rà soát command handler phía server và client;
- sửa trạng thái active/passive UDP;
- hoàn thiện `APPE`, `LIST` và data channel;
- chuẩn hóa reply FTP, bao gồm `503`, multiline `214` và multi-stage reply;
- refactor handler để một command có thể phát nhiều reply;
- tích hợp progress monitor cho truyền file;
- bảo đảm client và server không phụ thuộc trực tiếp vào nhau;
- kiểm tra shutdown server bằng `Ctrl+C`;
- cập nhật `README.md` và `ARCHITECTURE.md`.
- triển khai Active Upload ở cả server và client với handshake UDP;
- thêm lọc UDP peer, RDT cancellation và lifecycle cleanup cho session;
- phân tích ownership/thứ tự reply của `ABOR`;
- đánh giá mức độ đáp ứng `requirements.txt` và hướng hoàn thiện SHA-256;
- bổ sung test tự động cho Active Upload, peer filtering và cancellation/cleanup;
- hướng dẫn chạy client/server trên hai máy và các yêu cầu firewall/NAT.
- rà soát flow hiện tại và các defect phía client;
- lập kế hoạch xử lý giới hạn của `ABOR`, sau đó thu hẹp giải pháp theo đúng phạm vi trong `requirements.txt`.

## Ghi chú

- Nội dung prompt được sắp xếp theo thứ tự xuất hiện trong session.
- Một số lỗi được nhắc bằng số thứ tự như 1.1–1.6 và 2.1–2.3; ý nghĩa chi tiết của chúng phụ thuộc vào kết quả rà soát tại thời điểm tương ứng.
- Tài liệu này ghi lại yêu cầu của người dùng, không khẳng định mọi đề xuất trong phiên đã được triển khai hoàn chỉnh.
