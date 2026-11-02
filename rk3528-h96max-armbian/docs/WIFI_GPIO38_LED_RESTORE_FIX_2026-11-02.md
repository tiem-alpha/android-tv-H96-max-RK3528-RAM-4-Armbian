# Wi-Fi hoạt động khi chặn xung GPIO38 từ service LED

Ngày kiểm tra: 02/11/2026, trên H96 Max RK3528 của dự án, boot Armbian từ SD, kernel `6.1.172-vendor-rk35xx`. Đây là kết quả hai lần boot đối chiếu; chưa phải phép đo điện hoặc kiểm tra độ ổn định dài hạn.

## Kết quả và cách giữ cấu hình đang hoạt động

Giữ `armbian-led-state.service` ở trạng thái **masked**. Service này restore LED `pwr-wifi` trên GPIO1_PA6 (GPIO38), tạo xung xuống thấp ngay trước lúc Wi-Fi mất phản hồi. Sau khi chặn service, giữ nguyên driver/firmware/DTB, box tự kết nối Wi-Fi, nhận DHCP, scan và truy cập Internet thành công.

Áp dụng trên box tương ứng, rồi reboot:

```sh
sudo systemctl mask armbian-led-state.service
sudo reboot
```

Lệnh mask không có `--now`: không tác động GPIO trong phiên đang chạy. Không thử bật/tắt brightness hoặc trigger của `pwr-wifi` khi đang kiểm tra Wi-Fi. GPIO4_PA4/GPIO132 là chân reset Wi-Fi khác với GPIO38. DTB khai báo GPIO38 là LED; kết quả hiện tại chưa xác định chân đó thực tế ảnh hưởng nguồn, enable hay phần mạch nào.

## Hai lần boot đối chiếu

| Mục | Restore LED hoạt động | Restore LED bị chặn |
| --- | --- | --- |
| Boot ID | `267bea0d-2591-4b20-bc2b-517aa664b9bc` | `0713d6f3-86b8-4498-95de-4f50e01a3209` |
| GPIO38 | `1 → 0 → 1`, thấp khoảng 4,236 ms | Chỉ set mức cao ở init, không có xung thấp sau đó |
| Lần wake tiếp theo | CMD52 ghi function 1, reg `0x09=1` trả `-110` khoảng 1,122 s sau xung thấp | Không ghi nhận lỗi CMD52 trong giai đoạn Wi-Fi chạy |
| Scan/kết nối | Scan rỗng, `MM_START_REQ` timeout | Scan thấy nhiều AP; tự liên kết profile đã lưu |
| DHCP và truyền dữ liệu | Chưa kết nối | Có DHCP; ping gateway và Internet qua riêng `wlan0` thành công |
| Kernel | Không thấy NULL/Oops ở bản có guard | Không thấy wake fail, command timeout, queue crash hoặc Oops |
| Trace | Không mất/tràn bản ghi | Không mất/tràn bản ghi |

Kiểm tra truyền dữ liệu dùng `ping -I wlan0`, tránh nhầm lưu lượng Ethernet. Lượt kiểm tra ngắn có 3/3 phản hồi từ gateway Wi-Fi và 3/3 từ Internet, không mất gói.

## Vì sao service LED tạo xung

`/etc/armbian-leds.conf` lưu:

```ini
[/sys/class/leds/pwr-wifi]
trigger=none
brightness=1
```

`/usr/lib/armbian/armbian-led-state-restore.sh` có workaround: khi restore `trigger=none`, nó ghi `default-on`, sau đó ghi `none` rồi restore brightness. Trace thấy chính tiến trình `armbian-led-state` kéo GPIO38 thấp trong chuỗi này.

Điều này phù hợp với quan sát Wi-Fi hoạt động khi setup lần đầu rồi mất sau reboot: state LED có thể chỉ được lưu sau phiên đầu. Đây vẫn là giải thích có cơ sở, chưa có trace của lần setup đầu để xác nhận.

## Driver/firmware thực tế của phép thử thành công

- Repo: `https://github.com/gtxaspec/aic8800-wifi`, commit `a870f7f15170a5899bf0b98769896fd1a7d4bf1e`.
- Source chính: `SDIO/driver_fw/driver/aic8800`, release `2024_0929_2e313139`; không lấy source từ thư mục tích hợp ví dụ RK3326/RK3566.
- Chip được nhận theo SDIO `5449:0145` là `PRODUCT_ID_AIC8801`, revision 7. Không suy ra chip D80 từ tên thư mục firmware cũ.
- Có các sửa kiểm tra NULL và xử lý lỗi init; `CONFIG_PREALLOC_RX_SKB=y`, `CONFIG_SDIO_PWRCTRL=y`, clock SDIO 50 MHz.
- Toàn bộ 13 file firmware từ `SDIO/driver_fw/fw/aic8800` của cùng commit, ở `/lib/firmware/aic8800-gtx-a870f7f/SDIO/aic8800`. Bao gồm `fmacfw_patch.bin`; không trộn riêng file đó vào bộ Android.
- BSP SHA-256: `33b10d87c99e0eebd0c931d1a514bf4d6312dfe79d42cfdb37f27a0f4c6a7914`.
- FDRV SHA-256: `7667c62bfc6280642e516e4a8dfc7b0b86881b5b70e8c81104bfaf193135a898`.
- [Patch port đầy đủ trước RX preallocation](../evidence/armbian-wifi-2026-11-02/gtx-nullguard/full-port.patch), sau đó áp [patch RX preallocation](../evidence/armbian-wifi-2026-11-02/gtx-rxprealloc/rxprealloc.patch).

Kết quả này chưa chứng minh driver gốc cũng hoạt động chỉ bằng mask LED; hai boot đối chiếu dùng đúng cùng cặp GTX đã sửa. Cấu hình build image trong repo vẫn ghim nhánh driver trước đó; chưa tích hợp cặp GTX hoặc mask LED vào pipeline tạo image mặc định.

## Giới hạn và dữ liệu lưu

IOS, reset GPIO132 và pinmux SDIO không đổi trong khoảng trả lời cuối đến lỗi. Snapshot clock 32 kHz và SDIO ổn định; Bluetooth bật clock UART và cấu hình 1,5 Mbaud trước lỗi nhưng không có reset/đổi baud ở thời điểm lỗi. Chỉ riêng việc chặn LED restore trong lượt đối chiếu đã cho kết quả khác.

Trace phần mềm không đo điện áp/xung vật lý; snapshot 250 ms có thể bỏ lỡ thay đổi ngắn. Các event `power:clock_*` chưa bao phủ chắc chắn mọi thao tác gate của CCF. Trace có thể ảnh hưởng timing. Chưa kết luận loại trừ mọi nguyên nhân khác, hoặc bảo đảm Wi-Fi ổn định sau nhiều lần reboot/suspend.

- [Phân tích boot lỗi](../evidence/armbian-wifi-2026-11-02/boot-observe-267bea0d/ANALYSIS.md).
- [Phân tích boot thành công](../evidence/armbian-wifi-2026-11-02/boot-observe-noled-0713d6f3/ANALYSIS.md).
- [Cách bộ quan sát hoạt động](WIFI_BT_BOOT_OBSERVE_2026-11-02.md).

Raw trace, journal, binary module và firmware giữ tại máy phát triển; không đưa vào Git. Các báo cáo, patch và hash được lưu trong Git. Bộ trace đã tự trả boot options về cũ và disable hai service; riêng service LED tiếp tục masked để giữ cấu hình thành công.

## Kiểm tra Bluetooth sau khi Wi-Fi hoạt động

Trong cùng boot thành công, `h96max-bluetooth.service` và BlueZ đang chạy, HCI controller xuất hiện qua UART2 `/dev/ttyS2`, baud 1,5 Mbit/s. Ban đầu `bt_default` và `hci0` bị soft-block, controller báo `off-blocked`.

Đã dùng `rfkill unblock bluetooth` rồi `bluetoothctl power on`: thành công, controller chuyển `Powered: yes`. Scan 10 giây thấy ít nhất 12 thiết bị Bluetooth gần đó. Sau khi client scan kết thúc, controller báo `Discovering: no`; lệnh stop từ client khác báo Failed vì không còn phiên discovery đó. Không có HCI timeout/NULL/Oops trong kiểm tra. Wi-Fi tiếp tục liên kết và ping Internet qua riêng `wlan0` đạt 3/3 phản hồi sau lượt scan Bluetooth.

Bluetooth được để ở trạng thái bật sau kiểm tra. Đây là xác nhận bật radio/scan và kiểm tra đồng thời ngắn với Wi-Fi; chưa pair, truyền file hoặc thử âm thanh A2DP, chưa xác nhận trạng thái Bluetooth được giữ qua reboot.
