# Driver Wi-Fi từ Android trên box 192.168.0.4

ADB TCP kết nối thành công ngày 01/11/2026. Máy chạy kernel Android `5.10.157`, SDIO `5449:0145` và `544a:0146`; `aic8800_bsp` và `aic8800_fdrv` đang nạp. Đã sao chép nguyên bản ba module từ `/vendor_dlkm/lib/modules/` vào `modules/`. Hai file `.txt` chẩn đoán thô đã xóa theo yêu cầu.

| Module | SHA-256 | Ghi chú |
| --- | --- | --- |
| `aic8800_bsp.ko` | `d08c6bb8e19d90ce42e7df68b3376655540e57dcd5d2e554facb4ca4e02728ec` | `RELEASE_DATE:2023_0207_1037` |
| `aic8800_fdrv.ko` | `1d3bea6dfbef8504faf4f19c4679d1c6b8954f30c8fb144b6110f2a8ea3ec75e` | AIC8801 alias; version `6.4.3.0` |
| `aic8800_btlpm.ko` | `40852ecf26bcb75631be2be80f1aecfe656985e2984289810fac6afa9210f7f5` | Bluetooth low power |

Android nạp firmware `fw_patch_table_u03.bin`, `fw_adid_u03.bin`, `fw_patch_u03.bin`, `fmacfw.bin` từ `/vendor/etc/firmware/`. Log cho thấy firmware khởi tạo xong và nhiều lần scan trả `rwnx_rx_scanu_start_cfm()`. Không thấy `sdio wakeup fail` trong log đã thu.

**Khác biệt đáng chú ý:** bảng symbol và chuỗi trong BSP Android không có `aicwf_sdio_wakeup`, `aicwf_sdio_sleep_allow` hay thông báo `sdio wakeup fail`; driver nguồn Armbian hiện tại có các hàm này dưới `CONFIG_SDIO_PWRCTRL`, mặc định nguồn upstream bật `y`. Điều này phù hợp giả thuyết nhánh điều khiển ngủ SDIO gây lỗi trên Armbian, nhưng chưa chứng minh nguyên nhân duy nhất. Worktree build hiện ghi `CONFIG_SDIO_PWRCTRL := n` do một phép thử cũ; file đó không phải cấu hình của module gốc đang chạy và phép thử trước đã khiến box không trở lại qua mạng.

Module Android có `vermagic 5.10.157`; không thể nạp trực tiếp vào Armbian `6.1.172`. Chỉ dùng làm chuẩn đối chiếu khi sửa và build lại driver Linux. Không tìm thấy source driver trên phân vùng Android; ba file `.ko` là bản nhị phân gốc đã lấy được.
