# Nhật ký và hướng dẫn build Armbian cho H96 Max RK3528

**Trạng thái mới nhất sau khi boot thành công:** xem [TRANG_THAI_THUC_TE_2026-10-31.md](TRANG_THAI_THUC_TE_2026-10-31.md). Các mục "chưa boot" bên dưới là nhật ký lịch sử.

Tài liệu này ghi lại những việc đã làm trên box đang kết nối ADB và các lệnh để tiếp tục build, thử image từ thẻ SD. Các đường dẫn dưới đây tính từ thư mục `~/Project/H96_max_armbian/rk3528-h96max-armbian`.

## 1. Xác nhận đúng box qua ADB — đã thực hiện

```bash
adb devices -l
adb shell 'getprop ro.product.model; getprop ro.board.platform; uname -a'
adb shell 'cat /proc/device-tree/model'
```

Kết quả ghi nhận: `H96_Max_RK3528`, nền tảng `rk3528`, Android dùng kernel `5.10.157`, device tree báo `Rockchip RK3528 EVB2 DDR3 V10 Board`. Đây là **box cụ thể** được dùng để đối chiếu; các box khác cùng tên có thể lắp bo hoặc chip Wi-Fi khác.

## 2. Sao lưu device tree Android — đã thực hiện

Trên box này, `su 0` chạy được. DTB đang hoạt động nằm tại `/sys/firmware/fdt`; Android còn có phân vùng `dtbo`.

```bash
mkdir -p ~/Project/H96_max_armbian/device-tree-h96-max-rk3528
cd ~/Project/H96_max_armbian
adb exec-out su 0 cat /sys/firmware/fdt > device-tree-h96-max-rk3528/running.dtb
dtc -I dtb -O dts \
  -o device-tree-h96-max-rk3528/running.dts \
  device-tree-h96-max-rk3528/running.dtb
adb exec-out su 0 cat /dev/block/by-name/dtbo > device-tree-h96-max-rk3528/dtbo.img
```

Đã lưu `running.dtb`, `running.dts` và `dtbo.img` trong thư mục bên cạnh repo. `running.dts` chứa **serial, địa chỉ MAC và bootargs riêng của box**; không đăng công khai file này khi chưa xóa các thông tin đó.

DTB đang chạy gần như trùng với `dts/original-rk3528-evb2-ddr3-v10.dts` mà repo gốc cung cấp. Phần khác chủ yếu do bootloader thêm lúc boot: RAM, serial, MAC, initrd, logo và bootargs. DTB Android dùng làm **chuẩn đấu nối phần cứng**, không được chép nguyên vào kernel Armbian 6.1.

## 3. Kiểm tra ngoại vi thực tế — đã thực hiện

Android DTS ghi `wifi_chip_type = "ap6275s"`, nhưng thiết bị đang hoạt động là SDIO `5449:0145` và Android nạp driver họ `aic8800`. ID này là **AIC8801**. Cách kiểm tra lại:

```bash
adb shell 'su 0 cat /sys/bus/sdio/devices/mmc0:50b6:1/modalias'
adb shell 'su 0 lsmod'
```

Các kết nối đọc từ DTB đang chạy và được chuyển vào bản vá Linux:

| Thành phần | Kết quả từ Android | Cấu hình Armbian hiện tại |
| --- | --- | --- |
| Thẻ SD | Bộ điều khiển `mmc@ffc30000` hoạt động | `sdmmc` hoạt động, giới hạn 50 MHz để thử boot |
| eMMC | `mmc@ffbf0000` hoạt động trong Android | `sdhci` **disabled** trong DTB Linux |
| Ethernet | `gmac0`, RMII, PHY tích hợp | Bật `gmac0`, tắt `gmac1` của bo Hinlink nền |
| Wi-Fi | AIC8801 trên SDIO; chân bật GPIO4_PA4 | Sửa chân bật, tên chip, driver và firmware |
| Bluetooth | Android DTS khai báo UART2 và các chân điều khiển | Giữ cấu hình UART2 từ DTS nền; chưa thử Linux |
| HDMI | Hoạt động trên Android | Giữ tuyến HDMI của bản vá |
| AV composite | `tve` được bật trong Android | Bật `tve`, `route_tve`, `tve_in_vp1` |
| Âm thanh analog | `sai2` + `acodec`, chân PA GPIO0_PA0 | Bật card âm thanh analog tương ứng |
| USB | Nguồn host GPIO4_PB5, OTG GPIO4_PC1 | Thêm hai regulator 5 V và gắn vào USB PHY |
| LED, nút, IR | Android có LED Wi-Fi, phím ADC, remote IR | Sửa LED; nút và IR dùng DTS nền, chưa thử Linux |

Các dòng `status = "okay"` trong DTS mới chỉ cho phép driver thử nhận phần cứng. Chúng **không chứng minh** ngoại vi đã chạy trên Linux.

## 4. Bản vá đã cập nhật — đã thực hiện

- `patches/config/boards/rk3528-h96max.csc` chọn `rockchip/rk3528-h96max-stock-rails-net-hdmi.dtb`.
- `patches/patch/kernel/rk35xx-vendor-6.1/dt/` chứa DTS của H96 Max. Các file này dùng `rk3528-hinlink-ht2.dts` của kernel làm nền rồi sửa theo DTB của box.
- `patches/config/kernel/linux-rk35xx-vendor.config` bật module Wi-Fi AIC và hỗ trợ Bluetooth của driver AIC.
- `tools/capture-aic-firmware.py` lấy firmware từ Android. `patches/userpatches/customize-image.sh` đưa chúng vào image Linux.
- `patches/userpatches/bootenv/rockchip64.txt` cấu hình console hiển thị và UART0.

Firmware lấy từ box được Git bỏ qua; bản sao cục bộ đã nằm trong `patches/userpatches/overlay/lib/firmware/aic8800/`. Nếu clone repo sang máy khác, cần nối lại ADB và chạy bước lấy firmware.

## 5. Lấy firmware từ Android — đã thực hiện trên máy này

Chỉ cần chạy lại nếu thư mục firmware trên bị mất hoặc đổi máy build. Box phải đang chạy Android và kết nối ADB:

```bash
cd ~/Project/H96_max_armbian/rk3528-h96max-armbian
python3 tools/capture-aic-firmware.py
find patches/userpatches/overlay/lib/firmware/aic8800 -type f | wc -l
```

Lần thực hiện hiện tại đã lấy **37 file**. Nếu đã có đủ 37 file, bỏ qua bước này.

## 6. Đồng bộ bản vá sang Armbian — đã thực hiện, chạy lại sau mỗi lần sửa

```bash
cd ~/Project/H96_max_armbian/rk3528-h96max-armbian
```

Nếu chưa có `armbian-build/`:

```bash
git clone --depth=1 https://github.com/armbian/build.git armbian-build
```

Sau đó chép cấu hình, DTS và firmware overlay:

```bash
cp -R patches/. armbian-build/
grep BOOT_FDT_FILE armbian-build/config/boards/rk3528-h96max.csc
```

Kết quả `grep` phải là `rockchip/rk3528-h96max-stock-rails-net-hdmi.dtb`. Trên máy này, `armbian-build/` đã có và các file bản vá đã được đối chiếu là trùng với nguồn trong `patches/`.

## 7. Build image — lệnh cần chạy

```bash
cd ~/Project/H96_max_armbian/rk3528-h96max-armbian/armbian-build
CPUTHREADS="$(nproc)" ./compile.sh build \
  BOARD=rk3528-h96max \
  BRANCH=vendor \
  BUILD_MINIMAL=yes \
  BUILD_DESKTOP=no \
  RELEASE=trixie \
  KERNEL_CONFIGURE=no \
  KERNEL_GIT=shallow
```

`nproc` trên PC này trả `16`, nên lệnh trên dùng tối đa 16 luồng CPU theo yêu cầu. Nếu build bị trình quản lý bộ nhớ kết thúc (`Killed`, `Out of memory`), thử lại với ít luồng hơn. Trước khi chạy, kiểm tra cả hai phân vùng vì Docker/Containerd dùng `/`, còn dự án và cache Armbian dùng `/home`:

```bash
nproc
free -h
df -h / /home
```

Kiểm tra image khi build thành công:

```bash
ls -lh output/images/
```

Lần build Debian Trixie tối giản đã **hoàn tất** với kernel 6.1.172 sau 42 phút 47 giây. Image là `output/images/Armbian-unofficial_26.11.0-trunk_Rk3528-h96max_trixie_vendor_6.1.172_minimal.img` (khoảng 2,3 GB); `sha256sum -c` trả `OK`. Image có GPT với phân vùng boot và rootfs. Đã mount image chỉ đọc để kiểm tra: `armbianEnv.txt` chọn `rk3528-h96max-stock-rails-net-hdmi.dtb`; DTB này có eMMC `disabled`, TVE `okay`, Wi-Fi `aic8801`.

**Giới hạn quan trọng của image vừa build:** kernel Armbian 6.1.172 nhánh `rk-6.1-rkr7.2` không có thư mục driver `aic8800_sdio`, nên các tùy chọn `CONFIG_AIC_WLAN_SUPPORT` và `CONFIG_AIC8800_WLAN_SUPPORT` trong file cấu hình không xuất hiện trong `.config` cuối cùng. Firmware đã nằm trong rootfs, nhưng **Wi-Fi AIC8801 chưa thể hoạt động với image hiện tại**. Chưa thử boot thật, Bluetooth, HDMI, AV và USB trên Linux.

### Đối chiếu bootloader với multitool RK3528

[Multitool RK3528](https://github.com/paolosabatino/multitool/blob/master/sources/rk3528/boot_install) ghi `idbloader.img` tại sector `0x40` và `u-boot.itb` tại sector `0x4000` (sector 512 byte). Nhánh này **không dùng `loaderimage` hoặc `trust.img`**; hướng dẫn đóng gói hai file đó áp dụng cho những luồng boot Rockchip khác. Log UART firmware gốc của box này cũng báo `Trying fit image at 0x4000 sector`.

Đã so từng byte hai payload trong gói `linux-u-boot-rk3528-h96max-vendor` với image Armbian: cả hai đã nằm đúng vị trí của multitool. Để tái tạo và xác minh layout này từ image và gói U-Boot cùng phiên bản:

```bash
cd ~/Project/H96_max_armbian/rk3528-h96max-armbian
python3 tools/repack-rk3528-sd-image.py \
  armbian-build/output/images/Armbian-unofficial_26.11.0-trunk_Rk3528-h96max_trixie_vendor_6.1.172_minimal.img \
  armbian-build/output/debs/linux-u-boot-rk3528-h96max-vendor_26.11.0-trunk_arm64__2017.09-S39cd-P690a-H1795-Vb472-Bb936-R448a.deb \
  armbian-build/output/images/Armbian-unofficial_26.11.0-trunk_Rk3528-h96max_trixie_vendor_6.1.172_minimal-rk3528-sd.img
```

Bản đã đóng gói lại có SHA-256 `4b25c0270c130d38fc860268a5164556d00499cc8a21a30f26f0699bac9c4649`, **trùng hoàn toàn với image gốc**. Như vậy việc đóng gói lại không thay đổi nội dung và không tự giải quyết lỗi boot. [Thảo luận trên diễn đàn Armbian](https://forum.armbian.com/topic/59122-h96-max-rk3528-cannot-boot-armbian-from-tfsd-card/) ghi nhận kết quả khác nhau giữa các board: có máy không boot cả multitool, có máy boot với firmware gốc; một người xử lý lỗi đọc thẻ SD bằng cách giới hạn ở SDR25. DTS của dự án đã giới hạn `&sdmmc` ở 50 MHz và bỏ SDR50/SDR104, tương ứng mức tốc độ này khi Linux điều khiển thẻ. Thiết lập DTS chỉ có tác dụng **sau khi kernel được nạp**; nó không chữa lỗi đọc SD trong BootROM, SPL hoặc U-Boot. Một trường hợp khác trên diễn đàn chỉ boot Armbian sau khi vào recovery rồi reboot, cho thấy boot nóng và boot nguội cần được kiểm tra riêng. Cần log UART lúc bật nguồn của **box này khi cắm thẻ** để biết nó có đọc sector `0x4000` từ SD và lỗi ở giai đoạn nào. Không sửa eMMC chỉ để thử boot.

## 8. Ghi thẻ SD — chỉ sau khi build thành công

```bash
cd ~/Project/H96_max_armbian/rk3528-h96max-armbian/armbian-build
lsblk -o NAME,SIZE,MODEL,TRAN,MOUNTPOINTS
ls -lh output/images/*.img
```

Xác định đúng **toàn bộ thiết bị thẻ SD**, ví dụ `/dev/sdX` (không phải `/dev/sdX1`). Thay cả tên image và thiết bị trong lệnh sau bằng kết quả thực tế:

```bash
sudo dd if=output/images/TEN_IMAGE_THUC_TE.img of=/dev/sdX \
  bs=16M oflag=direct conv=fsync status=progress
sync
```

`dd` xóa toàn bộ dữ liệu trên thiết bị đích. Chỉ ghi vào thẻ SD. **Không dùng `armbian-install` hoặc công cụ flash eMMC** với bản thử này. Việc Linux vô hiệu hóa eMMC không thay đổi firmware hoặc thứ tự boot của ROM; stock firmware trên eMMC vẫn có thể tham gia giai đoạn boot đầu.

## 9. Kiểm tra sau khi boot Linux — chưa thực hiện

Cắm thẻ SD, HDMI và Ethernet rồi cấp nguồn. Bản build là `minimal`, nên không có desktop. Nếu vào được terminal hoặc SSH, chạy:

```bash
cat /proc/device-tree/model
cat /boot/armbianEnv.txt | grep fdtfile
lsblk -o NAME,SIZE,TYPE,MOUNTPOINTS
ip link
lsusb
ls /sys/class/drm
aplay -l
bluetoothctl list
sudo dmesg | grep -Ei 'mmc|sdio|aic|wifi|bluetooth|hdmi|tve|usb|acodec'
```

Kiểm tra `fdtfile` phải trỏ tới `rk3528-h96max-stock-rails-net-hdmi.dtb`; `lsblk` không nên hiển thị eMMC. Thử thực tế Wi-Fi, Bluetooth, HDMI, AV, âm thanh và từng cổng USB trước khi coi chúng là đã hỗ trợ. Nếu boot thất bại trước khi có màn hình, log UART 3,3 V sẽ hữu ích; cấu hình kernel chọn UART0 ở 1.500.000 baud.

## Phạm vi xác minh hiện tại

Đã xác minh kết nối ADB, DTB Android, SDIO ID, bản sao firmware, bản vá đã đồng bộ vào `armbian-build`, build image hoàn tất, checksum và DTB trong image. **Chưa xác minh** boot từ SD hay tính năng ngoại vi trên Linux. Wi-Fi hiện thiếu driver AIC8801 trong kernel; phải bổ sung driver và build lại trước khi thử Wi-Fi. Không thể bảo đảm mức hoạt động ngang Android chỉ từ device tree: driver, firmware và cấu hình người dùng của Linux cũng phải phù hợp.

## Trạng thái tạm dừng sau lần thử boot đầu tiên

- Image Trixie 6.1.172 đã được ghi vào thẻ SD 128 GB qua `/dev/sda`; `dd` hoàn tất và `cmp` đối chiếu toàn bộ 2.369.781.760 byte trên thẻ với image, kết quả trùng khớp. Thẻ đã được `eject` an toàn.
- Khi cắm thẻ vào H96 Max và cấp nguồn: HDMI đen, có con trỏ nhấp nháy rồi đứng yên; bàn phím USB dường như không phản hồi. Khi tháo thẻ và cấp nguồn lại, Android gốc vẫn chạy bình thường. Chưa có log UART, địa chỉ IP hay bằng chứng Linux đã vào userspace.
- Trên thẻ SD, đã xác nhận phân vùng boot `/dev/sda1` chứa kernel, initrd và DTB được `fdtfile` chỉ định. UUID của `rootdev` khớp phân vùng root `/dev/sda2`. Phân vùng root chưa có nhật ký systemd cho thấy Linux đã vào userspace.
- Đã sao lưu `/boot/armbianEnv.txt` thành `/boot/armbianEnv.txt.bak` trên thẻ, rồi sửa thành `verbosity=7`, `console=display`, `extraargs=cma=256M systemd.show_status=1`. File nguồn và bản sao trong Armbian checkout cũng có cấu hình này. Đây là bước chẩn đoán màn hình đen; chưa xác nhận nguyên nhân boot lỗi.
- Đã `sync`, unmount hai phân vùng và `eject` thẻ an toàn. Chưa build lại hoặc ghi lại image. Firmware Android/eMMC chưa bị ghi hoặc thay đổi.

**Bước tiếp theo:** cắm thẻ lại vào box, nối HDMI và Ethernet rồi cấp nguồn. Chụp ảnh hoặc ghi lại chữ/log cuối trên HDMI, nếu có. Nếu vẫn đứng ở con trỏ nhấp nháy, kiểm tra DHCP xem box có IP; nếu không có, thu log UART 3,3 V tại 1.500.000 baud. Chưa ghi eMMC.

Sau khi thử lại với `verbosity=7`, người dùng báo màn hình vẫn không có thay đổi. PC cùng mạng `192.168.1.0/24` quét ARP chỉ thấy router `192.168.1.1` và một thiết bị `192.168.1.4`; không thấy địa chỉ mới rõ ràng của box. `adb devices` cũng không thấy box. Kết quả mạng chỉ có ý nghĩa nếu cáp Ethernet đã nối với box. Chưa có log để xác định bootloader hay kernel là điểm dừng.

## Nhật ký lỗi build và cách xử lý

1. **`cp: cannot stat 'patches/*'`**: terminal ở thư mục chỉ chứa `armbian-build/`, chưa clone repo bản vá. Đã clone repo H96 Max rồi dùng đường dẫn đầy đủ hoặc `cd` vào repo trước khi chép.
2. **`cp: target 'armbian-build/': No such file or directory`**: terminal ở thư mục không có `armbian-build/`. Đã kiểm tra bằng `pwd` và `ls`, rồi clone Armbian bên trong repo H96 Max. Từ đó dùng `cd ~/Project/H96_max_armbian/rk3528-h96max-armbian` trước các lệnh tương đối.
3. **`arm64: not supported on this machine/kernel`**: Docker thiếu đăng ký QEMU `binfmt`; không phải thiếu RAM. Đã chạy `docker run --privileged --rm tonistiigi/binfmt --install arm64` và kiểm tra trong Docker bằng `arch-test arm64`, kết quả `arm64: ok`.
4. **`ORAS download failed` khi tải kernel shallow**: lần tải đã để lại `cache/git-bundles/kernel/linux-shallow-6.1.git.tar` (323 MB). Đã kiểm tra `tar -tf` đọc toàn bộ file thành công. Lần build kế tiếp dùng lại file này.
5. **`No rule to make target ...eltay-rm66-pdm.dtbo`**: cấu hình patch cũ của repo H96 Max ghi đè `0000.patching_config.yaml` mới của Armbian, bỏ mất `overlay-directories`. Đã đồng bộ cấu hình với Armbian hiện tại (`rk-6.1-rkr7.2` và mục chép overlay) ở cả `patches/` và `armbian-build/`. Đây là lỗi ở bước chuẩn bị overlay của Armbian, không phải DTS H96 Max.
6. **Phân vùng `/` đầy 100%**: `/home` vẫn còn dung lượng, nhưng `/var/lib/containerd` nằm trên `/` và dùng nhiều dung lượng. Đã chạy `docker builder prune --force` để dọn 2,593 GiB Docker build cache không còn dùng. Sau khi người dùng cho phép dọn image không dùng, đã xóa container `omnivoice` dừng 6 tuần và image `ghcr.io/debpalash/omnivoice-studio:latest`; giữ nguyên volume `omnivoice-data` và thư mục Hugging Face gắn ngoài. `/` sau đó còn khoảng 17 GiB.
7. **Chuẩn bị RAM cho lần build dùng 16 luồng**: RAM khả dụng chỉ khoảng 6 GiB và swap cũ 4 GiB. Đã thêm swap tạm 8 GiB tại `/home/armbian-build-extra.swap` bằng `fallocate`, `mkswap`, `swapon`; tổng swap hiện khoảng 12 GiB. File này chiếm 8 GiB trên `/home`, nên `/home` còn khoảng 22 GiB. Swap có thể khiến build chậm khi RAM đầy nhưng giúp tránh OOM. File swap không được thêm vào `/etc/fstab`, nên sau khởi động lại cần bật lại bằng `sudo swapon /home/armbian-build-extra.swap` nếu còn muốn dùng.

Sau lỗi số 5, build đã chạy lại và tạo image thành công. Các file đã build hoặc tải của Armbian trong `armbian-build/cache/`, `armbian-build/output/` và các Docker image Armbian được giữ nguyên. Sau build, `/home` chỉ còn khoảng 6,4 GiB, nên kiểm tra `df -h / /home` trước khi tạo thêm image. Tránh `docker system prune --volumes` vì nó có thể xóa volume dữ liệu của dự án khác.
