# Ứng viên thử AIC8801: flow control và re-probe

Hai module trong thư mục này được build ngoại tuyến từ kernel headers `6.1.172-vendor-rk35xx` có SHA-256 `.config` `10d9a538f42ffe441426e2616c3b5d99cb190e6586ff0a7960fce7a3d096b179` (trùng `/boot/config` trên box). Source là AIC8800 đã tích hợp trong kernel worktree; giữ `CONFIG_SDIO_PWRCTRL=y` như source gốc, áp duy nhất patch `0003-h96max-aic8801-defer-reprobe-and-log-cmd52-error.patch`.

| Module | SHA-256 |
| --- | --- |
| `aic8800_bsp.ko` | `6529fad86a267a6e914db12fe5a3062054ceb00ae82434d9d703def2cea3064f` |
| `aic8800_fdrv.ko` | `e6dd598ec10e711763eeee3b094036fddc180318da6ac4de436b4df1be637ced` |

`make modules` thành công. Cả hai có `vermagic` `6.1.172-vendor-rk35xx SMP mod_unload modversions aarch64`; bảng CRC symbol nhập khớp module gốc tương ứng. Cấu hình headers không đổi sau build. Compiler là Ubuntu GCC 14.2, cùng phiên bản chính với Debian GCC 14.2 dùng cho kernel nhưng khác bản phân phối. Chưa chạy module trên box, nên tính tương thích thực tế chưa được xác nhận.

Module gốc để khôi phục nằm trong `../aic8800_bsp-original.ko` và `../aic8800_fdrv-original.ko`. Khi triển khai, sao lưu module trên thẻ SD trước khi thay cả cặp, chỉ thử bằng cold boot, và giữ thẻ SD có thể tháo để phục hồi nếu boot lỗi. Không dùng hot unbind/reset SDIO hoặc dịch vụ trace lúc boot. Sau khi lên máy, chạy `tools/collect-aic8801-readonly.sh` và lấy `dmesg` để đọc lỗi CMD52 thực. Bản vá hiện nhắm vào Oops khi re-probe và khả năng quan sát lỗi flow control; chưa chứng minh đã sửa kết nối Wi-Fi.

## Kết quả thử cold boot

Đã triển khai cả cặp trên SD bằng `tools/stage-aic8801-flowctrl-reprobe.sh`; bản gốc trên box lưu tại `/var/backups/h96-wifi-flowctrl-20261101/`. Box boot, Ethernet/SSH hoạt động, hai `srcversion` module đang nạp khớp file ứng viên và không có Oops. `wlan0` vẫn không kết nối, scan rỗng. Dmesg cho thấy `aicwf_sdio_wakeup` thất bại ở ~49 giây, sau đó CMD52 đọc flow control `0x0a` trả `-110` (`ETIMEDOUT`) ở ~50 giây. Log ở `boot-test/`. Cần tiếp tục điều tra nguyên nhân chip không đáp ứng SDIO sau khi driver/firmware khởi tạo; bản vá này chưa sửa lỗi kết nối.
