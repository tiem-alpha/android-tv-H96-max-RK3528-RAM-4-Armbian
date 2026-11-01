# Phân tích `-110` khi AIC8801 đọc flow control

## `-110` thực sự xảy ra ở đâu

Kết quả đã ghi từ log cold boot với module thử (file `.txt` thô đã xóa theo yêu cầu):

- Giây 26–27: SDIO đã enumerate, BSP tải firmware, FDRV tạo `wlan0`.
- Giây 49,966–50,156: FDRV thử ghi thanh ghi wake `0x09` 20 lần và báo `sdio wakeup fail`; mã lỗi của bước ghi vẫn bị driver gộp thành `-1`.
- Từ giây 50,166: FDRV đọc thanh ghi flow control `0x0a` qua CMD52 và nhận `-110` (`ETIMEDOUT`).
- Giây 53: `MM_START_REQ` timeout, hàng lệnh hỏng; scan rỗng là hậu quả.

Đường đi trong source: `aicwf_sdio_flow_ctrl_msg()` → `aicwf_sdio_readb()` → Linux `sdio_readb()` → `mmc_io_rw_direct()` → CMD52 trên SDIO function 1. Driver host `dw_mmc.c` trả `-ETIMEDOUT` nếu có cờ `SDMMC_INT_RTO` (response timeout) **hoặc** bộ hẹn giờ host hết hạn khi không nhận được ngắt `CMD_DONE`. Vì vậy `-110` là lỗi giao dịch lệnh SDIO; **không phải** giá trị âm của thanh ghi flow control, lỗi mật khẩu, DHCP hay một mã lỗi trực tiếp từ firmware Wi‑Fi. Log hiện tại chưa phân biệt được hai nhánh timeout của host.

Driver còn một lỗi xử lý hậu quả rõ ràng: `aicwf_sdio_wakeup()` đặt `sdiodev->state = SDIO_ACTIVE_ST` sau vòng retry ngay cả khi cả 20 lần ghi wake đều thất bại; `aicwf_sdio_pwr_stctl()` bỏ qua giá trị trả về của hàm wake. Vì vậy driver tiếp tục đọc flow control và gửi lệnh trên một bus đã không thức. Sửa chỗ này sẽ ngăn hàng lệnh hỏng và giúp log đúng thứ tự, nhưng tự nó không làm chip trả lời CMD52 trở lại.

## Đối chiếu nguồn công khai

- [Hướng dẫn debug Wi‑Fi của D-Robotics](https://developer.d-robotics.cc/sdk_doc/versions/2.0.0/en/linux_development/driver_develop_guide/33-WIFI_Driver_Debug_Guide.html) mô tả CMD52 `-110` là timeout giao dịch thanh ghi và ưu tiên kiểm tra nguồn, clock của thiết bị. Phần CMD53 của tài liệu còn khuyên thử giảm 50 xuống 25 MHz và kiểm tra tín hiệu dữ liệu; đây là phép thử chẩn đoán, chưa phải kết luận cho box này.
- [Mã AIC8800 của Radxa](https://github.com/radxa-pkg/aic8800/blob/main/src/SDIO/driver_fw/driver/aic8800/aic8800_bsp/aicsdio.c) và [mã của FriendlyElec](https://github.com/friendlyarm/aic8800/blob/main/aic8800_bsp/aicsdio.c) có cùng mô hình wake/sleep và đọc flow control, nên không thấy bằng chứng rằng riêng thanh ghi `0x0a` trong bản port hiện tại bị chọn sai.
- [Báo cáo Armbian về SDIO `-110`](https://github.com/armbian/build/issues/10164) ban đầu nghi thời điểm cấp nguồn, nhưng tác giả kiểm tra lại và kết luận phần cứng board của họ xuống cấp. Đây là ví dụ cho thấy cùng mã lỗi có nhiều nguyên nhân, không phải trường hợp AIC8801 tương đương.
- [Tài liệu Rockchip Wi‑Fi/BT](https://github.com/Poco-Ye/rk_wifi_bt_android) cũng ghi trường hợp card SDIO đã enumerate nhưng đọc thanh ghi về `-110`; có hướng dẫn mở log MMC để phân biệt lỗi đường truyền. Nhận định phần cứng của tài liệu đó không thể áp thẳng cho H96 Max.

Không tìm thấy báo cáo công khai nào xác nhận đúng tổ hợp H96 Max RK3528 + AIC8801 + lỗi wake `0x09` rồi CMD52 `0x0a` `-110` và một bản sửa đã được kiểm chứng.

## Mức phù hợp của các giả thuyết

1. **Chip ngừng đáp ứng sau khởi tạo**: phù hợp nhất. Firmware tải xong và card hoạt động lúc giây 27; đến giây 49, cả ghi wake và đọc flow control đều lỗi. Có thể do nguồn/clock tại chip, chip treo hoặc tín hiệu CMD/CLK; phần mềm hiện chưa phân biệt được.
2. **Timing/chất lượng tín hiệu ở gần 50 MHz**: có thể. Host báo 49,8 MHz; driver tự đặt 50 MHz nên chỉ sửa `max-frequency` trong DTB không đủ. Cần thử bản 25 MHz ở cả BSP/FDRV trong một cold boot có log CMD52 để kiểm chứng. Android dùng 50 MHz nên đây vẫn chỉ là giả thuyết.
3. **Sai trạng thái sleep/wake trong driver hoặc firmware**: có thể góp phần; lần lỗi đầu xuất hiện khi đánh thức. Tuy nhiên thử FDRV bỏ sleep trước đây vẫn đọc flow control thất bại, nên chỉ bỏ sleep không giải quyết được.
4. **Runtime autosuspend của Linux**: kém phù hợp hơn, vì đã ép `power/control=on` trong phép thử trước mà lỗi vẫn còn.
5. **Profile Wi‑Fi, xác thực, DHCP**: loại khỏi nguyên nhân trực tiếp của `-110`, vì CMD52 lỗi trước khi gửi `MM_START_REQ` và trước khi kết nối.

Snapshot sau lỗi cho thấy GPIO cấp Wi‑Fi và reset ở mức bật, mux 32 kHz đúng, clock `clk_32k` đang enable, MMC2 báo nguồn bật/3,3 V/49,8 MHz. Đây là trạng thái kernel, **không phải phép đo vật lý** tại chân module. GPIO reset từng được điều khiển và card trả lời 155 CMD52 sau reset trong phép thử khác, nhưng hot reset làm driver Oops nên không lặp lại trên bản cũ; bản vá hiện tại chưa được thử hot reset.

## Phép thử phân biệt nguyên nhân

1. Bản build 25 MHz chỉ thay clock driver, giữ mọi cấu hình khác và cold boot. Nếu CMD52 ổn định và scan thành công, tập trung vào timing/đường SDIO. Nếu vẫn `-110`, 50 MHz đơn độc không phải lời giải.
2. Trong cold boot kế tiếp, ghi mã lỗi gốc của **lần ghi wake `0x09` đầu tiên** và trạng thái host MMC ngay trước đó. Log hiện tại biến mọi lỗi ghi thành `-1`, mất thông tin quan trọng nhất.
3. Nếu cả 25 MHz vẫn lỗi, đo thực tế nguồn Wi‑Fi, IO 3,3 V, 32 kHz, SDIO CLK và CMD tại module quanh giây 27–50. Chỉ phép đo này mới xác nhận sụt áp, mất xung hoặc chip không trả lời R5.

## Đối chiếu thêm với gợi ý từ Internet

- Android DTB của chính box (`evidence/android-192.168.0.4/peripherals/running.dts`) dùng SDIO 4 bit, `non-removable`, `mmc-pwrseq-simple`, reset GPIO4_PA4 và mux 32 kHz GPIO1_PC3. Nó khai báo `max-frequency` 200 MHz, nhưng driver chọn 50 MHz. Armbian hiện đã có reset và mux 32 kHz tương ứng; host đang chạy 4 bit và 49,8 MHz. Vì card đã enumerate và firmware nạp xong, `broken-cd`/thời gian chờ ngay trước lần detect đầu khó giải thích lỗi xuất hiện sau ~23 giây.
- CMD52 trao đổi byte thanh ghi trong phản hồi R5 trên đường CMD. Ép bus 1 bit chỉ bỏ DATA1–3; nó hữu ích để thử lỗi truyền dữ liệu CMD53, nhưng không phải phép thử trực tiếp nhất cho timeout phản hồi CMD52. Do đó giữ 4 bit khi thử 25 MHz để tách biến.
- `CONFIG_OOB=n` trong build hiện tại; FDRV dùng `sdio_claim_irq()`. Sai OOB GPIO không phải giả thuyết ưu tiên cho lỗi CMD52 này.
- BSP `aicbsp_platform_power_on()` không có nhánh điều khiển GPIO reset riêng trên build hiện tại (`CONFIG_PLATFORM_ROCKCHIP=n`); reset thuộc `mmc-pwrseq-simple` trong DTB. Log không cho thấy reset/tắt nguồn sau khi firmware nạp. Cần trace nguồn vật lý nếu nghi nguồn sụt khi chạy.
- `sdio_enable_func()` của function 1 thành công trước khi firmware tải; lỗi ở giây 49 không phải lỗi enable function ban đầu. Firmware hoặc trạng thái chip sau khi khởi tạo vẫn là khả năng mở.
- Đã thử cold boot với `FEATURE_SDIO_CLOCK` 25 MHz và bus 4 bit: MMC2 xác nhận 25 MHz, nhưng wake vẫn lỗi và CMD52 `0x0a` vẫn `-110`. Thử 1 bit khiến BSP lỗi truyền firmware `-110` sớm hơn, không có `wlan0`; đã trả bus 4 bit. Thêm delay pwrseq 200 ms vẫn lỗi wake/CMD52 sau nạp firmware. Bản định thử 10 MHz thực tế vẫn đặt clock 25 MHz và lặp lại lỗi; chưa có phép thử 10 MHz hợp lệ. Bản bỏ `non-removable` đồng bộ DTB/BSP/FDRV gây treo boot theo báo cáo người dùng; đường khôi phục nằm trong `docs/RECOVERY_WIFI_H96_2026-11-01.md`.

## Đánh giá giả thuyết `non-removable` và power cycle

- DTB Android **cũng có** `non-removable`, `mmc-pwrseq-simple`, reset GPIO4_PA4 và không khai báo `WIFI,poweren_gpio`/`WIFI,vbat_gpio` trong node WLAN. Vì vậy không có bằng chứng Android đang tắt hẳn một rail Wi‑Fi riêng qua các GPIO đó. `non-removable` làm MMC chỉ quét card một lần trong mỗi phiên host; nó không tự ngăn trình tự reset/power-up ở boot mới.
- Mã `mmc-pwrseq-simple` hiện có kéo reset assert ở `pre_power_on`, nhả ở `post_power_on`, assert ở `power_off`. Trace hot reset cũ đã thấy GPIO4_PA4 chuyển thấp/cao và chip trả lời 155 CMD52 sau đó. Đây là reset chân, **không chứng minh rail nguồn vật lý đã tắt**. Cold power cycle của toàn box cũng đã được thực hiện nhiều lần và lỗi vẫn lặp lại.
- BSP và FDRV AIC trước đây tự đặt `host->caps |= MMC_CAP_NONREMOVABLE` khi probe, rồi xóa khi remove. Vì vậy **chỉ xóa `non-removable` trong DTB sẽ không giữ host ở trạng thái removable sau khi driver nạp**. Phép thử đồng bộ đã bỏ thuộc tính trong DTB, thêm `broken-cd` và bỏ thao tác ép/xóa cờ ở hai module; box treo boot sau cold boot, chưa có log để quy nguyên nhân. Android gốc vẫn dùng `non-removable`, nên phải khôi phục cấu hình boot được trước khi thử hướng khác.
- Không lặp lại hot unbind/bind: phép thử trước đã điều khiển reset thành công nhưng FDRV probe trước BSP khiến kernel Oops. Bản vá mới chặn NULL pointer đó nhưng chưa chứng minh toàn bộ đường re-probe an toàn. Hot reset cũng không giống tắt hoàn toàn nguồn module.
