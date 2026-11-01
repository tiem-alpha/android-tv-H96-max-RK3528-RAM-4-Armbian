# Đối chiếu driver Wi-Fi Android gốc với bản build Armbian

Kiểm tra ngày 01/11/2026 trên các module đã trích từ box trong `evidence/android-192.168.0.4/modules/`.

| Dấu hiệu | Android gốc | Source Armbian hiện tại |
| --- | --- | --- |
| Tên module | `aic8800_bsp`, `aic8800_fdrv` | Giống tên |
| Phiên bản fdrv | `6.4.3.0` | `6.4.3.0` |
| Banner fdrv | `241c091M (master)` | Giống banner |
| Release BSP | `2023_0207_1037` | `2024_0327_3561b08f` |
| Release fdrv | `2023_0207_1041` | `2024_0327_3561b08f` |
| Kernel ABI | `5.10.157` | `6.1.172` |

Các chuỗi Android được đọc trực tiếp bằng `strings` và `modinfo` từ module gốc. Source build được ghim ở commit `ccf8fd059f70384fae4878c1048603510c2df700` của `queenkjuul/aic8800-milkv-duos`.

**Kết luận:** Bản source hiện tại cùng dòng 6.4.3.0 nhưng không giống bản Android. Các bản source công khai tìm được đến nay chỉ trùng banner/version; chưa tìm thấy bản phát hành có cả hai mốc `2023_0207_1037` và `2023_0207_1041`. Không thay commit build bằng một bản chưa chứng minh khớp. Module Android không nạp trực tiếp trên kernel Armbian 6.1 vì `vermagic` khác.

Để dùng đúng nhánh Android trên Armbian cần lấy source của release tháng 02/2023 (từ nhà cung cấp firmware/SDK hoặc một kho source có thể kiểm chứng), đối chiếu mã và cấu hình build với module gốc, rồi port và biên dịch cho kernel 6.1. Việc chỉ đổi chuỗi phiên bản hoặc chép `.ko` không đáp ứng yêu cầu này.

## Ứng viên source gần hơn đã kiểm tra

Kho `gtxaspec/aic8800-wifi`, commit `a870f7f15170a5899bf0b98769896fd1a7d4bf1e`, chứa nhánh SDIO Rockchip 3326 Android 8 tại `SDIO/patch/for_Rockchip/3326/Android8/mod/kernel/drivers/net/wireless/rockchip_wlan/aic8800/`. Nhánh này mang phiên bản `6.4.3.0`, cùng banner `241c091M (master)`, release `2023_0927_1224`, và nhận `5449:0145`/`5449:0146`. Đây là ứng viên gần Android gốc hơn về thời gian so với source tháng 03/2024 đang dùng, nhưng vẫn cách bản Android gốc khoảng bảy tháng.

Thử áp patch `0003-h96max-aic8801-defer-reprobe-and-log-cmd52-error.patch` lên nhánh này bằng `patch --dry-run`: hunk trong `aic_bsp_driver.c` và hunk đầu của `aicwf_sdio.c` áp được; hunk re-probe trong `aicwf_sdio.c` thất bại. Source này cũng còn `CONFIG_SDIO_PWRCTRL=y`, trong khi module Android gốc thiếu các hàm ngủ/thức SDIO. Vì vậy chưa thể chọn làm mặc định trước khi port patch, chỉnh cấu hình và build thử thành công.
