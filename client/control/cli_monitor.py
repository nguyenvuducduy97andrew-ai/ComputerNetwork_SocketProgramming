# Giao diện hiển thị trạng thái
# Vẽ thanh tiến trình trực quan khi truyền dữ liệu qua UDP
def draw_progress_bar(current_bytes, total_bytes, bar_length=50):
     # Tính toán tỷ lệ phần trăm hoàn thành
     percent = float(current_bytes) / total_bytes
     filled_length = int(bar_length * percent)
     
     # Tạo thanh tiến trình
     bar = '█' * filled_length + '-' * (bar_length - filled_length)
     
     # Hiển thị thanh tiến trình và phần trăm hoàn thành
     print(f'\r|{bar}| {percent:.2%} Complete', end='\r')
     
     # Khi hoàn tất, in dòng mới
     if current_bytes >= total_bytes:
         print()

