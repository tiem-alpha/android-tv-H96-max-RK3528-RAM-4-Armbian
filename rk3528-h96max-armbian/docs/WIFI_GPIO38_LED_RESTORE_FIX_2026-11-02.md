# Wi-Fi works when the LED-restore pulse on GPIO38 is blocked

Tested on 2026-11-02 on the project's H96 Max RK3528, booting Armbian from SD with kernel `6.1.172-vendor-rk35xx`. These are paired-boot results, not electrical measurements or long-duration reliability tests.

## Working configuration

Keep `armbian-led-state.service` **masked**. It restores the `pwr-wifi` LED on GPIO1_PA6 (GPIO38) and generated a brief low pulse immediately before Wi-Fi stopped responding. Blocking that service while retaining the same driver/firmware/DTB let the box auto-connect, obtain DHCP, scan and reach the Internet.

On the corresponding box:

```sh
sudo systemctl mask armbian-led-state.service
sudo reboot
```

Masking deliberately omits `--now`, so it does not change GPIO state in the current session. Do not change `pwr-wifi` brightness or trigger during the test. Wi-Fi reset GPIO4_PA4/GPIO132 is a different pin. Although the DTB labels GPIO38 as an LED, these results do not establish whether it physically controls supply, enable or another circuit.

## Paired boots

| Item | LED restore active | LED restore blocked |
| --- | --- | --- |
| Boot ID | `267bea0d-2591-4b20-bc2b-517aa664b9bc` | `0713d6f3-86b8-4498-95de-4f50e01a3209` |
| GPIO38 | `1 → 0 → 1`; low for about 4.236 ms | Initial high only; no later low pulse |
| Next wake | Function-1 CMD52 write `0x09=1` returned -110 about 1.122 s after pulse | No CMD52 error recorded during working Wi-Fi |
| Scan/association | Empty scan, `MM_START_REQ` timeout | Many APs, automatic association with saved profile |
| DHCP/traffic | No connection | DHCP and gateway/Internet ping explicitly over `wlan0` |
| Kernel | No NULL/Oops in guarded candidate | No wake/command timeout, queue crash or Oops |
| Trace | No lost/overrun records | No lost/overrun records |

Traffic checks used `ping -I wlan0` to avoid confusing Ethernet traffic with Wi-Fi. Gateway and Internet each returned 3/3 replies with no loss in these short tests.

## Why restoring an LED creates a pulse

`/etc/armbian-leds.conf` contained:

```ini
[/sys/class/leds/pwr-wifi]
trigger=none
brightness=1
```

`/usr/lib/armbian/armbian-led-state-restore.sh` uses a workaround when restoring `trigger=none`: it writes `default-on`, then `none`, then restores brightness. Tracing identified `armbian-led-state` pulling GPIO38 low during this sequence.

This is consistent with Wi-Fi working during initial setup and failing after reboot, since LED state may only be saved after the first session. No initial-setup trace exists to prove that explanation.

## Driver and firmware used for the successful trial

- Origin: `gtxaspec/aic8800-wifi`, commit `a870f7f15170a5899bf0b98769896fd1a7d4bf1e`.
- Generic `SDIO/driver_fw/driver/aic8800`, release `2024_0929_2e313139`; not the RK3326/RK3566 example integrations.
- SDIO `5449:0145` identifies `PRODUCT_ID_AIC8801`, revision 7. The old firmware-directory name does not establish a D80 chip.
- NULL/init error-handling fixes; `CONFIG_PREALLOC_RX_SKB=y`, `CONFIG_SDIO_PWRCTRL=y`, SDIO clock 50 MHz.
- All 13 files from `SDIO/driver_fw/fw/aic8800` at the same commit, installed under `/lib/firmware/aic8800-gtx-a870f7f/SDIO/aic8800`. Includes `fmacfw_patch.bin`; do not mix just that file into the Android set.
- BSP SHA-256: `33b10d87c99e0eebd0c931d1a514bf4d6312dfe79d42cfdb37f27a0f4c6a7914`.
- FDRV SHA-256: `7667c62bfc6280642e516e4a8dfc7b0b86881b5b70e8c81104bfaf193135a898`.
- [Full port patch before RX preallocation](../evidence/armbian-wifi-2026-11-02/gtx-nullguard/full-port.patch), followed by the [RX preallocation patch](../evidence/armbian-wifi-2026-11-02/gtx-rxprealloc/rxprealloc.patch).

The pair does not prove the original driver would work with LED masking alone. Both trials used the same patched GTX pair. The current pipeline bundles that source with both patches already applied, matching firmware, masked LED restore and Bluetooth unblock/AutoEnable settings. A fresh image still needs hardware validation. The FD655 date/time display uses different GPIOs and remains enabled.

## Limits and retained evidence

IOS, reset GPIO132 and SDIO pinmux did not change between the final successful response and the failure. Clock snapshots showed stable 32 kHz/SDIO state. Bluetooth enabled its UART clock and selected 1.5 Mbaud beforehand, but no reset/baud change coincided with failure. Blocking LED restore was the intentional difference between the paired trials.

Software tracing does not measure physical voltage. Snapshots every 250 ms can miss short events; `power:clock_*` coverage does not prove every CCF gate operation was captured. Trace overhead may affect timing. The results neither exclude every other cause nor establish reliability across many reboots/suspend cycles.

- [Failing-boot analysis](../evidence/armbian-wifi-2026-11-02/boot-observe-267bea0d/ANALYSIS.md).
- [Successful-boot analysis](../evidence/armbian-wifi-2026-11-02/boot-observe-noled-0713d6f3/ANALYSIS.md).
- [Observation design](WIFI_BT_BOOT_OBSERVE_2026-11-02.md).

Raw traces/journals, module binaries and factory firmware were retained locally rather than committed. Reports, patches and hashes preserve the investigation. The collector restored boot options and disabled its two services after capture; LED restore stayed masked. Bundled GTX firmware in the current build is a separate, explicit exception to the earlier policy of keeping firmware outside Git.

## Bluetooth after Wi-Fi recovery

In the successful boot, `h96max-bluetooth.service` and BlueZ ran, with the HCI controller on UART2 `/dev/ttyS2` at 1.5 Mbit/s. Initially `bt_default` and `hci0` were soft-blocked and the controller was `off-blocked`.

`rfkill unblock bluetooth` followed by `bluetoothctl power on` succeeded (`Powered: yes`). A ten-second scan found at least 12 nearby devices. After the scanning client ended, discovery stopped; stopping from another client failed because its discovery session was absent. No HCI timeout/NULL/Oops appeared. Wi-Fi remained linked and Internet ping explicitly over `wlan0` still returned 3/3 replies.

Bluetooth was left powered on. This verifies basic power-on/discovery and short simultaneous Wi-Fi use, not pairing, file transfer, A2DP or persistence through reboot.
