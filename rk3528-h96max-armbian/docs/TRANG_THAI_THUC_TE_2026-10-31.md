# H96 Max RK3528: trạng thái thực tế sau khi boot từ SD (31/10/2026)

Tài liệu này ghi kết quả đã kiểm tra trên **box đang dùng**, với Armbian Trixie desktop, kernel `6.1.172-vendor-rk35xx`. Các ghi chép thử boot cũ trong `HUONG_DAN_H96_MAX_RK3528.md` là lịch sử và không còn mô tả trạng thái hiện tại.

## Đã xử lý và xác minh

### Kernel đọc được thẻ SD và mount rootfs

- Trước khi sửa: U-Boot nạp được kernel/initrd từ SD, nhưng kernel không khởi tạo được `mmc0` tại `ffc30000.mmc`. Log có `Busy; trying anyway`, `Timeout sending command (cmd 0x202000 ...)`, `error -110 whilst initialising SD card`, rồi rơi vào `(initramfs)`. Hai thẻ khác nhau cho cùng hiện tượng. `0x202000` là lệnh cập nhật clock của bộ điều khiển DW MMC; không phải lệnh đọc rootfs.
- Rootfs của image đã được kiểm tra riêng: `bootfs` và `rootfs` đều có mặt, ext4 qua `e2fsck -fn` không báo lỗi, UUID `rootdev` trong `armbianEnv.txt` trùng UUID của rootfs. File image được ghi lên thẻ và đối chiếu byte thành công.
- DTB Android đang chạy trên box (`../device-tree-h96-max-rk3528/running.dts`), DTS Android gốc (`dts/original-rk3528-evb2-ddr3-v10.dts`) và DTS Hinlink nền đều đã có pin CLK/CMD/DET/DATA0-3 và hai nguồn `vcc_sd`/`vccio_sd`. Cảnh báo thiếu pinctrl `normal`/`idle` không chứng minh pin SD hoặc regulator bị xóa.
- Bản sửa ở `patches/patch/kernel/rk35xx-vendor-6.1/dt/rk3528-h96max-stock-rails.dts`, trong `&sdmmc`: thêm pinctrl `normal` và `idle` cùng nhóm chân với `default`; thêm `no-1-8-v`, `no-sdio`, `no-mmc`; bỏ các chế độ UHS SDR12/25/50/104; giảm `max-frequency` từ 50 MHz xuống 25 MHz. `&sdhci` (eMMC) vẫn `disabled`. Không thêm hoặc đổi regulator SD.
- Đã biên dịch DTS thành DTB với `dtc -@` rồi **chỉ chép đè** `/boot/dtb/rockchip/rk3528-h96max-stock-rails-net-hdmi.dtb` trên thẻ. Không cần build lại kernel hoặc flash lại image cho phép thử này. DTB cũ được sao lưu trên PC tại `/tmp/h96-sdmmc-test/original-on-card.dtb`; đây là file tạm, có thể mất sau khi PC dọn `/tmp`.
- Sau khi thay DTB, log xác nhận `mmcblk0p2` được mount/remount làm root, `mmcblk0p1` được mount tại `/boot`, systemd chạy tới màn hình login và rootfs tự mở rộng theo dung lượng thẻ. Box hiện boot được từ SD, Ethernet và SSH hoạt động ở `192.168.0.3` tại lần kiểm tra cuối.

**Giới hạn kết luận:** các thuộc tính SDMMC được thay đồng thời, nên chưa biết thuộc tính nào là nguyên nhân quyết định. Image desktop có sẵn được build trước bản sửa; DTB trên thẻ đã được thay riêng. Nếu ghi lại image desktop cũ lên thẻ, phải thay DTB lần nữa hoặc build image mới từ DTS hiện tại.

### Chạy headless qua Ethernet

- Trên box, `ssh.service` đã `enabled` và `active`; profile Ethernet được đặt `connection.autoconnect=yes`.
- `sleep.target`, `suspend.target`, `hibernate.target`, `hybrid-sleep.target`, `suspend-then-hibernate.target` đã bị mask. `/etc/systemd/logind.conf.d/90-h96-headless.conf` đặt `IdleAction=ignore` và bỏ qua các phím nguồn/ngủ/ngủ đông.
- Sau một lần boot lại, SSH tự hoạt động ở `192.168.0.3`. Đây là IP DHCP hiện tại, không phải địa chỉ tĩnh được bảo đảm.

## Lỗi còn tồn đọng

1. **Wi-Fi AIC8801 chưa kết nối được** ([nhật ký chi tiết](BUG_WIFI_AIC8801.md)). SDIO nhận thiết bị `5449:0145` và tạo `wlan0`, firmware được nạp, nhưng scan không thấy mạng. `wpa_supplicant` báo `CTRL-EVENT-SCAN-FAILED ret=-16`; kernel báo `aicwf_sdio_wakeup: sdio wakeup fail` và `reg:9 write failed`. Profile `NguyenTiem ` đã lưu mật khẩu, nên lỗi không chỉ là thiếu profile. Ethernet vẫn hoạt động. Đã thử biên dịch/cài hai module AIC với `CONFIG_SDIO_PWRCTRL` tắt; sau reboot box không xuất hiện trên mạng. Đã **khôi phục hai module cũ** từ `/var/backups/h96-wifi-20261031/` trên rootfs và xác nhận box boot, SSH lại được. Không dùng bản module thử nghiệm đó; cấu hình build trong repo đã được trả về như trước.
2. **HDMI chỉ hiện sau khi rút/cắm lại.** DRM đôi khi nhận `HDMI-A-1` là `connected`, nhưng log có nhiều `dwhdmi-rockchip: ddc read failed`. Chưa xác định lỗi HPD/DDC, EDID, tuyến VOP hay trình quản lý màn hình. Chưa có bản sửa HDMI.
3. **Reboot nóng không ổn định.** Có lần box không quay lại trên Ethernet, màn hình đen với con trỏ nhấp nháy. Sau khi khôi phục module cũ và cấp nguồn từ trạng thái tắt, box lên lại. Chưa có UART của lần treo để quy nguyên nhân cho module thử nghiệm, bootloader hay SD handoff; tránh coi reboot nóng đã được xác minh.
4. **Serial getty còn trỏ tới `ttyFIQ0`.** Log systemd báo chờ `/dev/ttyFIQ0` quá hạn, trong khi console Linux đang dùng `ttyS0`. Đây không phải nguyên nhân cản rootfs boot, nhưng cần sửa unit getty nếu muốn login ổn định qua UART.
5. **Ngoại vi khác chưa được xác minh đầy đủ:** Bluetooth, composite AV, analog audio và từng cổng USB. Các cảnh báo OPP/SCMI/OP-TEE riêng lẻ chưa được chứng minh là nguyên nhân của các lỗi trên.

## Điểm cần giữ khi thử tiếp

- Chi tiết lỗi Wi-Fi, bằng chứng và từng phép thử: [BUG_WIFI_AIC8801.md](BUG_WIFI_AIC8801.md). Trạng thái mới nhất: box boot với DTB có mux 32 kHz và module AIC gốc; Ethernet/SSH hoạt động, Wi-Fi vẫn lỗi `sdio wakeup fail`; không có Oops ở lần boot gần nhất.
- Giữ DTB SDMMC đang boot được. Không ghi eMMC/Android; chỉ thử trên SD.
- Giữ Ethernet cắm và sao lưu trước khi thay module. Không nạp `aic8800_bsp-awake.DO-NOT-LOAD.ko` hoặc hai module `CONFIG_SDIO_PWRCTRL=n` đã thử.
