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

## Ghi chú

- Nội dung prompt được sắp xếp theo thứ tự xuất hiện trong session.
- Một số lỗi được nhắc bằng số thứ tự như 1.1–1.6 và 2.1–2.3; ý nghĩa chi tiết của chúng phụ thuộc vào kết quả rà soát tại thời điểm tương ứng.
- Tài liệu này ghi lại yêu cầu của người dùng, không khẳng định mọi đề xuất trong phiên đã được triển khai hoàn chỉnh.
