# Ngoại vi Android: FD655, LED, AV, HDMI

Đã lưu `running.dtb`, DTS giải mã, `kernel.config`, `FD655_Demo` và `init.rk3528.rc` từ box.

| Ngoại vi | Bằng chứng Android | Tình trạng Armbian |
| --- | --- | --- |
| Màn hình LED 7 đoạn | `CONFIG_LEDS_FD655=y`, `fd655_dev`, `/dev/fd655_dev`; chân GPIO4 số 19 và 20 | Kernel 6.1 hiện không có source FD655. Cần port driver hoặc viết bộ điều khiển phù hợp. |
| Giờ và trạng thái mạng | `FD655_Demo` khởi chạy sau `sys.boot_completed`; binary dùng `time`, `localtime`, `wlan0`, `eth0`, `ioctl` | Cần chương trình Linux mới dùng tên mạng thực tế và giao diện FD655 sau khi port. |
| LED nguồn/Wi-Fi | `gpio-leds/pwr-wifi` dùng GPIO1 số 6; `default-state = "on"`, trigger `none` | DTS Armbian đã khai báo chân này. Có thể điều khiển qua `/sys/class/leds/`. |
| AV composite | `CONFIG_ROCKCHIP_DRM_TVE=y`; DRM có `card0-TV-1` | Kernel Armbian có driver TVE và DTS bật route TVE. Cần xác minh trên box khi boot Linux. |
| HDMI | `CONFIG_ROCKCHIP_DW_HDMI=y`; DRM có `card0-HDMI-A-1` | Kernel Armbian có driver HDMI và DTS bật route HDMI. Cần xác minh trên box khi boot Linux. |

FD655, TVE và HDMI là driver tích hợp trong kernel Android. Không có file `.ko` riêng để sao chép. File `FD655_Demo` là chương trình Android, không chạy trực tiếp trên Debian. Đèn `pwr-wifi` chỉ là một GPIO LED; trạng thái Wi-Fi và Ethernet trên màn hình 7 đoạn do chương trình điều khiển quyết định.

Đã clone source [`linux_openvfd`](https://github.com/arthur-liberman/linux_openvfd) vào `evidence/linux_openvfd` tại commit `775bdf8c0f6e959a6e9de043ee6838fe947994c6`. Dự án này liệt kê FD655/FD6551, nhưng chưa được cấu hình hoặc kiểm chứng với chân của box này. Đây không phải source driver Android gốc.

Log Android cho thấy HDMI xuất 1920×1080p60. TVE từng bật 720×576i50 rồi tắt. Trạng thái cổng AV chưa được xác minh bằng hình ảnh thực tế.
