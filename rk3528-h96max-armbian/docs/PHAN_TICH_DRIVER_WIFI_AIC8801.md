# Phân tích driver Wi-Fi AIC8801 trên H96 Max RK3528

## Đường hoạt động

1. SDIO phát hiện chức năng `5449:0145` và `544a:0146`.
2. `aic8800_bsp` chọn AIC8801, đặt clock SDIO 50 MHz và nạp firmware U03.
3. `aic8800_fdrv` đăng ký `wlan0` qua cfg80211. Scan đi qua hàng lệnh SDIO đến firmware.
4. Firmware gửi xác nhận scan và các khung nhận về qua ngắt SDIO.

Log Android của đúng box xác nhận các bước 1–4. Android dùng kernel `5.10.157`; BSP có ngày phát hành `2023_0207_1037`. Android quét nhiều lần và nhận `rwnx_rx_scanu_start_cfm()`.

## Điểm khác đã xác nhận

| Thành phần | Android | Armbian đang lỗi |
| --- | --- | --- |
| BSP SDIO power control | Binary không có `aicwf_sdio_wakeup`, `aicwf_sdio_sleep_allow` | Source upstream bật `CONFIG_SDIO_PWRCTRL=y` |
| FDRV SDIO power control | Binary có `aicwf_sdio_wakeup` và `aicwf_sdio_sleep_allow` | Source cũng bật nhánh này; log lỗi wake đến từ FDRV |
| Firmware | Nạp `fw_patch_table_u03.bin`, `fw_adid_u03.bin`, `fw_patch_u03.bin`, `fmacfw.bin` | File đã trích từ chính box; MD5 trên Linux đã khớp Android |
| Clock SDIO | Driver đặt 50 MHz | Source Linux cũng yêu cầu 50 MHz |
| DT clock 32 kHz | Android mux chân GPIO1_PC3 | DTB Linux đã thêm mux, nhưng scan vẫn lỗi |
| Dynamic firmware PS | Android `ps_on=Y`, `dpsm=N` | Source Linux mặc định tương ứng `true`, `false` |

Trong FDRV Armbian, `aicwf_sdio_sleep_allow()` ghi `0x10` vào thanh ghi `0x05` sau khoảng 30 ms rảnh. Lần gửi kế tiếp gọi `aicwf_sdio_wakeup()`, ghi `0x01` vào thanh ghi `0x09`, rồi đọc lại `0x05`. Log `reg:9 write failed` trỏ đúng thanh ghi wake `0x09` của AIC8801. Đây là lỗi giao tiếp SDIO tại bước đánh thức, trước xác thực và DHCP. FDRV Android cũng có đường wake tương tự; bản Android hoạt động cho thấy chỉ sự hiện diện của nhánh power control không đủ giải thích lỗi.

Có lỗi xử lý tiếp theo trong source: `aicwf_sdio_wakeup()` đặt trạng thái nội bộ thành `SDIO_ACTIVE_ST` ngay cả khi wake thất bại. `aicwf_sdio_pwr_stctl()` bỏ qua mã lỗi trả về. Đường truyền tiếp tục như chip đã thức. Điều này có thể làm scan kẹt hoặc trả `-16`; chưa chứng minh toàn bộ triệu chứng chỉ do nhánh này.

## Vì sao chưa thể kết luận bản build `CONFIG_SDIO_PWRCTRL=n` đã chữa được

Worktree build hiện có `CONFIG_SDIO_PWRCTRL := n`, nhưng đây là di tích của phép thử cũ. Module build đó đã khiến box không trở lại qua mạng sau reboot. Không có UART của lần treo. Một module thử khác dùng `.config` và compiler không khớp, gây kernel Oops khi `insmod`, trước khi chạy logic Wi-Fi. Module ứng viên mới build với headers khớp vẫn chưa được nạp thử. Vì vậy chưa có phép thử sạch để xác nhận việc tắt power control giải quyết lỗi.

## Hướng sửa có thể kiểm chứng

1. Build BSP từ đúng headers, compiler và symbol versions của kernel đang chạy.
2. Thử từng thay đổi riêng trên BSP và FDRV. Boot lạnh với BSP không sleep đã xác nhận lỗi FDRV vẫn còn.
3. Nạp thử trong phiên có Ethernet, UART và bản sao module gốc. Ghi log từ probe đến scan.
4. Chỉ khi scan ổn định, kiểm tra bắt tay WPA và lưu lượng DHCP.
5. Nếu vẫn lỗi, so sánh luồng SDIO, ngắt và clock bằng log hai kernel. Không coi `-16` là lỗi mật khẩu hoặc DHCP.

Không nạp module Android `5.10.157` vào kernel Armbian `6.1.172`. Source Android gốc không có trên phân vùng đã kiểm tra; ba file `.ko` đã lưu tại `evidence/android-192.168.0.4/modules/`.
