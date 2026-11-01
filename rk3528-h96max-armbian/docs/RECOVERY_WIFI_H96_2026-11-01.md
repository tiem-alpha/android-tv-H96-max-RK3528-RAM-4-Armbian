# Theo dõi thay đổi và khôi phục Wi‑Fi H96 Max

## Bật eMMC để chuẩn bị cài Armbian

Sau khi box boot lại từ SD và SSH hoạt động, đã chuẩn bị DTB `emmc-enabled-from-baseline.dtb` nhưng người dùng hoãn cài eMMC. DTB trên SD đã được trả về baseline trước khi thử Wi-Fi tiếp; eMMC vẫn `disabled` và **chưa ghi eMMC**.

## Bản DTB Wi-Fi đối chiếu Android đang chờ cold boot

Đã stage `android-wifi-match.dtb` (SHA-256 `2900b5df495ca78ee7b3f45ca966314d72fd8b096f3f9fe0e6815113c445022f`) trên SD. So với baseline boot được, chỉ thêm `rockchip,use-v2-tuning` cho `/mmc@ffc10000` và đổi `wifi_chip_type` từ `aic8801` thành chuỗi `ap6275s` của DTB Android. Đã kiểm tra `non-removable` vẫn có, `broken-cd` không có, eMMC vẫn `disabled`; module BSP/FDRV không đổi. Baseline khôi phục tại `/var/backups/h96-wifi-dtb-baseline-20261101.dtb` (SHA-256 `ca21b5d1031287a0d01e7bb09419397642f1f97fbffd4d7f6f620281a4e688ee`). Có SSH thì chạy `sudo bash /home/nguyentiem/h96-wifi-25mhz-20261101/stage-aic8801-dtb-variant.sh baseline`; nếu không boot được thì chép file backup vào đường DTB đang dùng qua máy tính. Chưa cold boot bản mới.

Ngày 01/11/2026, kernel box `6.1.172-vendor-rk35xx`, root trên thẻ SD `/dev/mmcblk0p2`, `/boot` trên `/dev/mmcblk0p1`. Ethernet SSH `192.168.0.3` hoạt động trước khi thử 25 MHz. Không sửa eMMC/Android.

## Trạng thái hiện tại: phép thử bỏ `non-removable` gây treo boot

Box không phản hồi Ethernet/SSH sau cold boot bản polling. Chưa xác định chính xác thay đổi nào gây treo; không lặp lại phép thử này. Khi thẻ SD được cắm vào máy tính, khôi phục BSP, FDRV và DTB từ `/var/backups/h96-wifi-polling-20261101/` trước. Đã chuẩn bị `evidence/armbian-wifi-2026-11-01/dtb-test-variants/android-wifi-match.dtb` để đối chiếu riêng phần Wi-Fi với Android, **chưa stage/chưa boot**. Bản đó giữ `non-removable`, bỏ `broken-cd`, bật `rockchip,use-v2-tuning` và trả `wifi_chip_type` về `ap6275s`; các GPIO SDIO/pwrseq vẫn là GPIO4_PA4 và GPIO1_PC3 như Android.

Ngày 01/11 đã stage và cold boot phép thử SDIO polling; box treo boot theo báo cáo người dùng. DTB thử đã bỏ `non-removable`, thêm `broken-cd`, giữ bus 4 bit và reset `mmc-pwrseq-simple`; nhãn WLAN của Armbian lúc đó là `aic8801`, khác chuỗi `ap6275s` trong DTB Android gốc. BSP và FDRV thử bỏ thao tác tự đặt/xóa `MMC_CAP_NONREMOVABLE`, giữ `CONFIG_SDIO_PWRCTRL=y` và BSP chọn 25 MHz. Bản build cuối có vá chặn con trỏ NULL khi probe lại và log mã lỗi CMD52; bản build đầu thiếu hai vá đã được thay trước cold boot. Bản 10 MHz trước đó thực tế vẫn chạy 25 MHz và vẫn lỗi CMD52 `-110`, nên không được tính là phép thử 10 MHz.

| File trên box | SHA-256 đã stage |
| --- | --- |
| BSP `aic8800_bsp.ko` | `42515356169396cd6a2e1bade927e037db982d68e9257af609427e12a1f781e1` |
| FDRV `aic8800_fdrv.ko` | `59e5955bac7e249ef82259130678a3869bf5f99d11cf45de462bd270979cf914` |
| DTB `rk3528-h96max-stock-rails-net-hdmi-wifi32k.dtb` | `526ed8531a1d446b97faee2923c665d3a23b1efd67369a35c1d82c58e7903526` |

Ba file trước phép thử đã sao lưu tại `/var/backups/h96-wifi-polling-20261101/` và kiểm tra hash: BSP `de0c2ad395e3e6417363cf1a581a9f519c6420a57dc83fea13081e2a5666bdd5`, FDRV `e6dd598ec10e711763eeee3b094036fddc180318da6ac4de436b4df1be637ced`, DTB `ca21b5d1031287a0d01e7bb09419397642f1f97fbffd4d7f6f620281a4e688ee`. Nếu SSH còn hoạt động, chạy `sudo bash /home/nguyentiem/h96-wifi-25mhz-20261101/restore-aic8801-polling-test.sh` rồi cold boot. Nếu box không lên, tháo thẻ SD và chép ba file từ thư mục backup vào đúng đường module/DTB ghi trong bảng dưới, sau đó unmount an toàn. Không có dịch vụ trace tự khởi động và không sửa eMMC/Android.

### Trạng thái trước phép thử polling

| Mục | Trạng thái trên SD | SHA-256 |
| --- | --- | --- |
| BSP `/lib/modules/6.1.172-vendor-rk35xx/kernel/drivers/net/wireless/aicsemi/aic8800/aic8800_bsp/aic8800_bsp.ko` | Bản thử 10 MHz, giữ patch re-probe/log | `de0c2ad395e3e6417363cf1a581a9f519c6420a57dc83fea13081e2a5666bdd5` |
| FDRV `/lib/modules/6.1.172-vendor-rk35xx/kernel/drivers/net/wireless/aicsemi/aic8800/aic8800_fdrv/aic8800_fdrv.ko` | Bản thử flow-control, không đổi khi stage 25 MHz | `e6dd598ec10e711763eeee3b094036fddc180318da6ac4de436b4df1be637ced` |
| DTB được chọn trong `/boot/armbianEnv.txt` | `rockchip/rk3528-h96max-stock-rails-net-hdmi-wifi32k.dtb`; baseline bus 4 bit, không thêm delay | `ca21b5d1031287a0d01e7bb09419397642f1f97fbffd4d7f6f620281a4e688ee` |
| Boot/trace service | Không cài dịch vụ trace lúc boot; dịch vụ oneboot cũ disabled | — |

BSP 50 MHz ngay trước phép thử nằm ở `/var/backups/h96-wifi-25mhz-20261101/aic8800_bsp-50mhz.ko` (SHA-256 `6529fad86a267a6e914db12fe5a3062054ceb00ae82434d9d703def2cea3064f`). Cặp module gốc trước mọi thử nghiệm nằm ở `/var/backups/h96-wifi-flowctrl-20261101/` (BSP `a8ad26ea7466b520fc74a5a712cefbee76d42e371b87943026c116a8d46900c7`; FDRV `96ac9fb52005ad33a4e0d900da8ad47539a976f4e86f161ff75ccccba946d5de`). Bản sao module gốc còn có trong `evidence/armbian-wifi-2026-11-01/` ở máy phát triển.

Đã chuẩn bị hai DTB độc lập trong `evidence/armbian-wifi-2026-11-01/dtb-test-variants/` và `/home/nguyentiem/h96-wifi-25mhz-20261101/` trên box: `sdio-1bit.dtb` chỉ đổi `bus-width=1`; `pwrseq-delay-200ms.dtb` chỉ thêm `post-power-on-delay-ms=200`. Sau cold boot 25 MHz với bus 4 bit, MMC2 xác nhận 25 MHz nhưng wake vẫn lỗi và CMD52 `0x0a` vẫn `-110`; log ở `evidence/armbian-wifi-2026-11-01/clock-25mhz-candidate/boot-test/`. Sau cold boot 25 MHz + 1 bit, card vẫn enumerate nhưng BSP gửi firmware lỗi `aicwf_sdio_send_pkt fail-110` từ giây 26, FDRV không nạp và `wlan0` không xuất hiện; log ở `evidence/armbian-wifi-2026-11-01/dtb-test-variants/boot-test-1bit/`. Sau cold boot 25 MHz + 4 bit + delay 200 ms, firmware lại nạp xong nhưng wake thất bại rồi CMD52 `0x0a` `-110` ở giây 49; log ở `evidence/armbian-wifi-2026-11-01/dtb-test-variants/boot-test-delay200/`. **Đã trả DTB baseline và stage BSP 10 MHz cho cold boot kế tiếp.**

Script `tools/stage-aic8801-dtb-variant.sh` (đã chép vào cùng thư mục trên box) có các chế độ `1bit`, `delay200`, `baseline`; kiểm tra SHA-256 và lưu DTB baseline vào `/var/backups/h96-wifi-dtb-baseline-20261101.dtb` trước lần đổi đầu. Đã chạy `1bit`, `delay200`, rồi `baseline`; bản baseline trên box có SHA-256 `ca21b5d1031287a0d01e7bb09419397642f1f97fbffd4d7f6f620281a4e688ee`. Giữ cùng tên DTB trong `armbianEnv.txt` để không thêm biến boot khác.

BSP 10 MHz nằm ở `evidence/armbian-wifi-2026-11-01/clock-10mhz-candidate/aic8800_bsp.ko` và `/home/nguyentiem/h96-wifi-25mhz-20261101/aic8800_bsp-10mhz.ko` trên box (SHA-256 `de0c2ad395e3e6417363cf1a581a9f519c6420a57dc83fea13081e2a5666bdd5`). Đã stage bằng `tools/stage-aic8801-10mhz-test.sh`; BSP 25 MHz sao lưu tại `/var/backups/h96-wifi-10mhz-20261101/aic8800_bsp-25mhz.ko` (SHA-256 `ce23114d5e2f79dc3f7cfe6fced25da93bac29c01d3cf8b34a64f3aa1ca73a5c`).

## Khôi phục khi box vẫn có SSH

Chạy trên box với quyền root:

```sh
bash /home/nguyentiem/h96-wifi-25mhz-20261101/restore-aic8801-modules.sh original
bash /home/nguyentiem/h96-wifi-25mhz-20261101/stage-aic8801-dtb-variant.sh baseline
```

Script kiểm tra SHA-256 bản gốc, thay cả BSP/FDRV, chạy `depmod` và `sync`. Cần **rút nguồn 10 giây rồi cắm lại** để module gốc được nạp. Chọn `50mhz` thay cho `original` nếu muốn quay về cặp bản vá trước phép thử clock.

## Khôi phục khi treo logo, không có SSH

Rút nguồn, tháo SD cắm vào máy tính. Mount phân vùng root (`mmcblk0p2`) ở chế độ ghi; chép hai file `aic8800_bsp-original.ko` và `aic8800_fdrv-original.ko` từ `var/backups/h96-wifi-flowctrl-20261101/` trên phân vùng root vào đúng hai đường module nêu trong bảng. DTB đang boot hiện là baseline; nếu hash khác `ca21b5d1031287a0d01e7bb09419397642f1f97fbffd4d7f6f620281a4e688ee`, mount thêm phân vùng boot (`mmcblk0p1`) và chép `var/backups/h96-wifi-dtb-baseline-20261101.dtb` từ root vào `dtb/rockchip/rk3528-h96max-stock-rails-net-hdmi-wifi32k.dtb` trên boot. Unmount thẻ an toàn, cắm lại box và cold boot. Nếu có `depmod` trong chroot tương thích ARM thì chạy; nếu không, module cùng tên/đường dẫn vẫn được nạp bởi cấu hình boot hiện tại và có thể chạy `depmod -a` sau khi SSH lên.

Không dùng hot unbind/bind MMC hoặc reboot nóng để khôi phục; các phép thử trước đã làm SDIO kẹt và từng gây kernel Oops. Giữ `bootlogo=false` và `plymouth.enable=0` để thấy lỗi boot trên HDMI.
