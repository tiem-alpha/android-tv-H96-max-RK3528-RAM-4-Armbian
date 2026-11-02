# Tích hợp Wi-Fi/Bluetooth vào image

Pipeline hiện dùng cấu hình radio đã kiểm tra trên box thay cho nhánh driver cũ.

## Thành phần của build

- `patches/config/h96-aic8800.conf`: repo, commit, thư mục source/firmware và đường dẫn cài thống nhất.
- `patches/config/h96-aic8800-firmware.sha256`: hash của đủ 13 file firmware cùng commit GTX.
- `tools/prepare-aic8800-gtx.sh`: lấy source đúng commit, từ chối checkout đã sửa source/firmware, xác thực hash và tạo overlay. `build-desktop.sh` tự gọi script này. Có thể chạy riêng với `bash tools/prepare-aic8800-gtx.sh`.
- `patches/patch/misc/aic8800-gtx/`: hai patch đã thử trên box: port/NULL/init guards và bật RX preallocation. Patch `misc/aic8800/0003...` cũ còn được giữ để tra cứu, không nằm trong danh sách patch của extension mới.
- `patches/extensions/h96max-aic8801.sh`: ghép source vào kernel, sửa đường dẫn Kconfig, bật BSP/FDRV dạng module, thêm source/patch/manifest vào cache key. Giữ SDIO 50 MHz, power control và RX preallocation bật.
- `patches/userpatches/customize-image.sh`: cài và kiểm tra bộ firmware GTX, mask service LED để tránh xung GPIO38, cài FD655 như trước.
- Post-image hook xác thực lại firmware, thiết lập autoload BSP trước FDRV, mask LED, tạo service Bluetooth UART2 1,5 Mbaud với `rfkill unblock bluetooth`, bật BlueZ và `AutoEnable=true`.
- `/etc/h96-radio-build.conf` trong image ghi commit và cấu hình radio để kiểm tra sau boot. Image không cài/bật các service trace thử nghiệm.

Không cần trích firmware Android để build cấu hình GTX. Bộ firmware Android đã lưu chỉ dùng cho lịch sử/khôi phục driver cũ. Firmware GTX và source cache được tải từ repo ghim, binary không đưa vào Git.

## Build trên checkout mới

Từ thư mục `rk3528-h96max-armbian`:

```sh
git clone --depth=1 https://github.com/armbian/build.git armbian-build
H96_BUILD_THREADS=8 ./build-desktop.sh
```

Nếu đã có `armbian-build`, cần kiểm tra đó là Git checkout riêng hợp lệ. Script từ chối thư mục chỉ còn cache/source nhưng mất `.git`, để tránh Armbian nhận nhầm Git repo cha. Không xóa cache hoặc output cũ chỉ để vượt kiểm tra này. Có thể dùng checkout Armbian mới theo hướng dẫn README.

Firmware tự tải trước khi compile; lỗi checksum làm build dừng. Khi offline, dùng source cache đã chuẩn bị; kernel source cache của Armbian vẫn phải có revision tương ứng. `H96_AIC_SOURCE_DIR` cho phép script chuẩn bị firmware dùng một checkout sạch có sẵn, nhưng không bỏ qua kiểm tra commit/hash.

## Kiểm tra đã thực hiện

1. Fetch thực từ GitHub và xác thực đủ 13 hash firmware; kiểm tra cú pháp shell.
2. Chạy hook ghép kernel hai lần trên staging riêng: patch không chồng lặp và Kconfig/Makefile không bị thêm trùng.
3. So sánh toàn bộ `.c`, `.h` và Makefile của source được hook tạo với source GTX RX-preallocation đã boot thành công: trùng nội dung. Kconfig được sửa riêng đường dẫn tích hợp.
4. Chạy Kconfig `olddefconfig` trên cây Kconfig tối thiểu: vendor AICSEMI và AIC_WLAN_SUPPORT bật; FDRV/BTLPM dạng module; đường dẫn firmware đúng.
5. Build lại module từ source do hook tạo, bằng headers `6.1.172-vendor-rk35xx` và GCC 14. Kiểm tra vermagic và toàn bộ CRC symbol nhập của BSP/FDRV đạt.
6. Chạy `customize-image.sh` thật trong chroot x86 tối thiểu riêng, sau đó chạy post-image hook hai lần với `systemctl --root` (không start service). Xác nhận firmware đúng, LED mask, autoload, FD655 enable, Bluetooth enable, rfkill trước attach, AutoEnable và metadata. Policy BlueZ có sẵn vẫn giữ các giá trị khác.
7. Cố ý làm hỏng một file firmware trong rootfs thử: post-image hook từ chối. Kiểm tra build script từ chối thư mục Armbian mất Git metadata trước khi gọi Docker/compile.

Workspace kiểm tra: `/home/nguyentiem/h96-image-integration-check`, log build module ở `build.log`. Đây là kiểm tra thành phần pipeline, chưa phải một image mới hoàn chỉnh đã flash/boot. Armbian upstream hiện chưa được ghim commit; cần lưu revision và build log của mỗi lần build. Máy hiện có thư mục Armbian thiếu `.git`, nên chưa chạy full image build tại đó.

## Xác nhận sau khi flash image mới

```sh
cat /etc/h96-radio-build.conf
systemctl is-enabled armbian-led-state.service  # masked
nmcli device wifi list
ip -4 addr show wlan0
bluetoothctl show
systemctl status h96max-bluetooth.service --no-pager
```

Kiểm tra lại Wi-Fi qua reboot, DHCP và truyền dữ liệu, Bluetooth power-on/scan. Pairing, A2DP, suspend và kiểm tra dài hạn chưa được xác nhận. Giữ Ethernet/khôi phục SD khi thử image mới; giữ Android/eMMC như giới hạn boot hiện tại của dự án.
