# Reverse driver AIC8801 Android bằng REA

Nguồn: các module `.ko` đã trích từ Android chạy trên chính box, ở `evidence/android-192.168.0.4/modules/`. Phân tích tĩnh bằng REA CLI 6.8.0, Ghidra 12.1.4; Evidence JSON nằm trong `evidence/android-192.168.0.4/rea/`. Pseudocode là kết quả dịch ngược, không phải source gốc. Không thực thi module Android trên Armbian.

## Kết quả đã xác nhận

| Nhánh | Android `.ko` | Source Armbian | Kết luận |
| --- | --- | --- | --- |
| `aicwf_sdio_flow_ctrl_msg` | Đọc thanh ghi flow control qua `sdio_readb`; khi lỗi trả `-1`, khi giá trị bằng 0 thử tối đa 50 lần; mask `0x7f` cho AIC8801 | Cùng logic, thanh ghi `0x0a` | `buffer_cnt=-1` là lỗi giao dịch SDIO, không phải hết bộ đệm. Nhánh này không cho thấy khác biệt giải thích lỗi. |
| Gửi lệnh qua `sdio_bustx_thread` | Gọi flow control trước khi `sdio_writesb`; thử lại tối đa 10 lần; nếu vẫn lỗi thì không gửi gói | Cùng trình tự và ngưỡng | `MM_START_REQ` bị chặn do không đọc được thanh ghi trước khi firmware nhận lệnh. |
| `aicwf_sdio_wakeup` và `sleep_allow` | Có cả ghi sleep `0x10`, ghi wake và đọc xác nhận; khi wake thất bại vẫn đặt trạng thái nội bộ thành active | Cùng hành vi chính | Lỗi trạng thái nội bộ là điểm yếu chung; riêng sự hiện diện của nhánh sleep không giải thích vì sao Android hoạt động. |
| `aicwf_sdio_func_init` | Đặt block size 512, enable function, đặt clock theo BSP, ghi các thanh ghi cấu hình và wake, đợi 5 ms rồi đọc sleep register | Cùng trình tự chính | Không thấy khác biệt khởi tạo hiển nhiên ở FDRV. |
| `aicbsp_get_feature` | Bảng clock theo chip; log của đúng box xác nhận chọn 50 MHz | BSP Armbian chọn 50 MHz | 50 MHz tự nó không phải khác biệt đã xác nhận. |

## Khoanh vùng

Ở lần boot lạnh FDRV bỏ sleep, giao dịch đọc flow control đầu tiên bị lỗi khoảng giây 48, sau khi SDIO đã nhận chip và firmware đã nạp ở giây 25–26. `MM_START_REQ` không được gửi thành công; `cmd timed-out` và ghi thanh ghi wake `0x09` sau đó là hậu quả. Giả thuyết cần ưu tiên là trạng thái chip/nguồn/clock, host SDIO của kernel 6.1, hoặc tương tác BSP–firmware trước lúc FDRV đọc. Mức 50 MHz là phép thử phụ về biên tín hiệu, không phải bản sửa đã chứng minh.

## Phép đo tiếp theo

`tools/trace-aic8801-sdio.sh` dùng tracepoint `mmc_request_start/done` của riêng `mmc2` để lấy `cmd_err`, `data_err` và opcode mà không thay module. Đã chạy thử 8 giây trên box: script hoạt động, thấy clock 50 MHz, 3,3 V, 4 bit; trace rỗng vì hàng lệnh đã hỏng trước lúc bắt đầu đo. Cần bắt trace **trước lỗi đầu tiên của một lần khởi tạo mới**; thử rescan trên phiên đã crash không tái tạo được lệnh đọc `0x0a`. Mã lỗi gốc hiện bị FDRV biến thành `-1`; trace MMC ở lần khởi tạo tiếp theo sẽ phân biệt timeout, CRC và lỗi host khác.

Ngày 01/11 đã cài `h96-aic8801-boot-trace.service` trên box để tự ghi 90 giây đầu boot vào `/var/log/h96-aic8801-boot-trace`. Dịch vụ đã được `systemd-analyze verify` và bật. Sau lệnh reboot từ xa, box không quay lại Ethernet; sau lần người dùng cấp nguồn lại, box vẫn chưa xuất hiện trên LAN tại thời điểm ghi dòng này. **Chưa đọc được trace boot; không suy diễn mã lỗi MMC.** Cần kiểm tra HDMI/UART hoặc tháo thẻ SD đọc file log trên máy build nếu Ethernet tiếp tục không lên.

### Khôi phục sau lỗi boot

Journal trên thẻ cho thấy unit trace có `Before=systemd-udevd.service` nhưng lại đợi `systemd-journald.service`. `udevd` chỉ bắt đầu khoảng giây 112, sau khi thiết bị `/boot` đã timeout ở giây 114; `local-fs.target` thất bại. Đây là lỗi thứ tự systemd do unit trace gây ra. Đã gỡ unit, liên kết `sysinit.target.wants` và script trên thẻ; hai module AIC vẫn khớp SHA-256 bản gốc. Phân vùng boot và root qua `e2fsck -fn` không báo hỏng. Đã tắt `bootlogo`/Plymouth trong `/boot/armbianEnv.txt` để thấy log; bản sao trước thay đổi là `/boot/armbianEnv.txt.before-boot-diagnostic`.

Sau khi cắm lại thẻ, box boot thành công lúc 09:14: `systemctl is-system-running` trả `running`, `/boot` mount từ `/dev/mmcblk0p1`, Ethernet/SSH hoạt động, unit trace không còn. Wi-Fi vẫn disconnected. Không dùng lại unit trace có ràng buộc `Before=systemd-udevd.service`.
