# Thử nghiệm LED FD655 của H96 Max

Log driver Android trên box ghi CLK là GPIO4 line 20 và DAT là GPIO4 line 19. Dịch vụ này gửi lệnh FD655 bằng GPIO hai dây theo giao thức của `evidence/linux_openvfd`. Mỗi chu kỳ 60 giây, màn hình hiện `DD/MM` trong 15 giây (dấu phân cách sáng liên tục), rồi `HH:MM` trong 45 giây (dấu hai chấm nhấp nháy). Biểu tượng Ethernet/Wi-Fi sáng khi interface tương ứng có carrier và `operstate=up`. Có thể đổi thời lượng bằng `date_seconds` và `time_seconds` trong `/etc/h96-fd655.json`.

Trên box Armbian, sao chép thư mục `led` sang box, rồi chạy `sudo ./install-on-box.sh`. Xem lỗi bằng `journalctl -u h96-fd655 -b`. Thử dữ liệu mà không điều khiển GPIO bằng `python3 h96-fd655.py --dry-run`.

Đã xác nhận LED sáng trên box với CLK/DAT đảo theo log Android. Trước khi bật dịch vụ, kiểm tra `/dev/gpiochip4` có đúng bank GPIO4 trên kernel đang chạy (`gpioinfo`) và hai line 19/20 còn trống. Nếu ký tự hoặc icon sai vị trí, chỉnh `grid` và `icon_bits` trong `/etc/h96-fd655.json` rồi khởi động lại dịch vụ. `grid` là thứ tự RAM của icon và bốn chữ số; `icon_bits` là vị trí bit 0–7 của từng biểu tượng.

Wi-Fi chỉ sáng khi radio tạo được interface và kết nối; lỗi khởi tạo AIC8801 hiện tại sẽ làm biểu tượng này tắt. Dịch vụ không điều khiển LED nguồn `pwr-wifi` riêng trên GPIO1.
