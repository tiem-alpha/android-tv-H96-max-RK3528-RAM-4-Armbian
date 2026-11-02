# H96 Max RK3528 Armbian image

This repository builds a Debian Trixie XFCE image for the H96 Max RK3528 box used in this project. The image includes the H96 Max device tree, vendor kernel, SD boot support, Ethernet, HDMI configuration, AIC8801 Wi-Fi modules and firmware, Bluetooth setup, and the FD655 front-panel clock and network indicators.

**Hardware baseline:** SD boot, Ethernet and the FD655 display work on the tested box. Wi-Fi scanning, DHCP and Internet traffic, plus Bluetooth power-on/discovery, were verified with the pinned GTX driver and GPIO38 LED-restore workaround now included in this build pipeline. A freshly rebuilt image and long-term stability still need hardware validation; other limits appear below.

The board name alone does not identify the hardware. Check that your box uses RK3528 and that its Wi-Fi device is SDIO `5449:0145` before using this image. The Android device tree calls the Wi-Fi chip `ap6275s`, but the live device and Android driver identify AIC8801.

## 1. Get the repository and tools

Use a Linux build host with Internet access, Git, Python 3, Docker, and enough free space for an Armbian build. Docker must be running. On an x86-64 host, the build script uses a privileged Docker container to register ARM64 QEMU/binfmt. Armbian Build may request host packages or root privileges during its first run.

```bash
sudo apt update
sudo apt install -y git python3 docker.io xz-utils util-linux
sudo systemctl enable --now docker

git clone https://github.com/tiem-alpha/android-tv-H96-max-RK3528-RAM-4-Armbian.git
cd android-tv-H96-max-RK3528-RAM-4-Armbian/rk3528-h96max-armbian
```

If your clone has a different directory name, enter its `rk3528-h96max-armbian` directory. Run all remaining build commands from that directory. Confirm the build files are present:

```bash
ls -l build-desktop.sh patches/config/boards/rk3528-h96max.csc led/h96-fd655.py
```

## 2. Pinned Wi-Fi driver and matching firmware

The image uses `gtxaspec/aic8800-wifi` at commit `a870f7f15170a5899bf0b98769896fd1a7d4bf1e`, generic `SDIO/driver_fw/driver/aic8800`, with the checked-in kernel 6.1/init-guard patches. RX preallocation and SDIO power control are enabled, and the SDIO clock is 50 MHz. The build masks `armbian-led-state.service` to prevent the GPIO38 pulse found in the paired boot traces.

`build-desktop.sh` automatically downloads all 13 matching firmware files from the same commit and verifies every SHA-256 before starting Armbian Build. Firmware binaries are not committed here. You do not need Android/ADB firmware extraction for this configuration. To prepare/check firmware separately:

```bash
bash tools/prepare-aic8800-gtx.sh
```

The source cache is `armbian-build/cache/h96-aic8800-gtx/COMMIT/`. The generated firmware overlay is `patches/userpatches/overlay/lib/firmware/aic8800-gtx-a870f7f/SDIO/aic8800/`. Source/firmware settings and expected hashes are in `patches/config/h96-aic8800.conf` and `h96-aic8800-firmware.sha256`.

For an existing clean checkout of the pinned repo, set `H96_AIC_SOURCE_DIR=/absolute/path/to/aic8800-wifi` when running the preparation script or build script. The checkout must have the exact commit and no source/firmware edits; the kernel extension fetches the same pinned commit independently. `tools/capture-aic-firmware.py` remains available to archive factory firmware, but that archive is not used by the GTX image.

## 3. Build the image

Clone Armbian Build *inside this directory*. Use an existing checkout only if it still contains its own valid Git metadata; a directory containing cached build files without `.git` is not sufficient. The script copies the current board files, patches, firmware overlay, and LED files into that checkout before every build.

```bash
git clone --depth=1 https://github.com/armbian/build.git armbian-build
H96_BUILD_THREADS=8 ./build-desktop.sh
```

Choose a smaller positive `H96_BUILD_THREADS` value if the host has limited RAM. The script fetches and verifies the firmware and checks the LED files before starting Armbian Build. It selects:

| Setting | Value |
| --- | --- |
| Board | `rk3528-h96max` |
| Kernel branch | `vendor` (Rockchip 6.1 family) |
| Distribution | Debian `trixie` |
| Image | XFCE desktop, mid tier, non-minimal |
| Boot device tree | `rockchip/rk3528-h96max-stock-rails-net-hdmi.dtb` |
| Wi-Fi | Pinned GTX AIC8801 BSP/FDRV, init guards, matching firmware, 50 MHz, RX preallocation |
| GPIO38 | LED restore service masked from the first boot |
| Bluetooth | UART2 HCI at 1.5 Mbaud, rfkill unblock, BlueZ AutoEnable |
| FD655 display | Python program, configuration, `python3-libgpiod`, enabled systemd service |

The build result is under `armbian-build/output/images/`. Use the filename actually produced on your host:

The [radio integration notes](docs/BUILD_RADIO_INTEGRATION_2026-11-02.md) describe the pinned source, firmware checks, GPIO38 fix and component validation. The pipeline has been checked through kernel-module compilation and isolated rootfs customization; a newly built full image still needs a boot test.

```bash
find armbian-build/output/images -maxdepth 1 -type f \( -name '*.img' -o -name '*.img.xz' \) -printf '%f\n'
```

Armbian's upstream `build` branch can change. This repository does not pin an upstream Armbian commit, so a future fresh clone may need compatibility fixes. Keep the Armbian Build revision and build log when reporting a failure.

## 4. Write the image to an SD card

The image is intended for SD boot with the stock Android firmware still on eMMC. The current device tree disables eMMC. **Do not use `armbian-install` or flash this image to eMMC.** Identify the entire SD-card device carefully; the following command erases it.

```bash
lsblk -o NAME,SIZE,MODEL,TRAN,MOUNTPOINTS
```

Set the two variables to your actual image filename and whole SD-card device, such as `/dev/sdX` rather than `/dev/sdX1`. Run only the command that matches your image format:

```bash
# For a compressed image:
image_path='armbian-build/output/images/REPLACE-WITH-YOUR-IMAGE.img.xz'
sd_device='/dev/REPLACE-WITH-YOUR-SD-CARD'
xzcat "$image_path" | \
    sudo dd of="$sd_device" bs=16M oflag=direct conv=fsync status=progress

# Or, for an uncompressed image:
image_path='armbian-build/output/images/REPLACE-WITH-YOUR-IMAGE.img'
sd_device='/dev/REPLACE-WITH-YOUR-SD-CARD'
sudo dd if="$image_path" of="$sd_device" bs=16M oflag=direct conv=fsync status=progress
sync
```

Insert the card, connect Ethernet and HDMI, then power the box from a fully off state. First boot can take longer while Armbian expands the root filesystem and performs initial setup. Keep access to the SD card so you can recover from a bad build without changing Android on eMMC.

## 5. Verify the booted image

Open a terminal on HDMI or connect over Ethernet. The address comes from DHCP; do not assume the development box's address is yours.

```bash
cat /proc/device-tree/model
uname -r
cat /boot/armbianEnv.txt | grep -E 'fdtfile|rootdev'
lsblk -o NAME,SIZE,TYPE,MOUNTPOINTS
ip -br addr
find /lib/modules/"$(uname -r)" -name 'aic8800_*.ko*'
cat /etc/h96-radio-build.conf
systemctl is-enabled armbian-led-state.service  # expected: masked
ls /lib/firmware/aic8800-gtx-a870f7f/SDIO/aic8800/
systemctl status h96-fd655.service --no-pager
journalctl -u h96-fd655.service -b --no-pager
```

The FD655 service shows `DD/MM` for 15 seconds and `HH:MM` for 45 seconds. The Ethernet and Wi-Fi icons follow each interface's link state. Change timing, brightness, or display mapping in `/etc/h96-fd655.json`, then run `sudo systemctl restart h96-fd655.service`. The program expects GPIO4 at `/dev/gpiochip4`, with line 19 for clock and line 20 for data. See [LED details](led/README.md).

## Known problems and limits

| Component | Current status | What to do |
| --- | --- | --- |
| SD boot and root filesystem | Booted on the tested box after the SD controller device-tree fix. | If boot stops at initramfs with `mmc` timeout or `-110`, confirm the image includes the current DTS and try another SD card. Read the UART log before changing bootloader settings. |
| Ethernet | Working on the tested box. | Check `ip -br addr`, the cable, and DHCP if SSH is unavailable. |
| HDMI | Picture may appear only after unplugging and reconnecting HDMI. Logs have shown `ddc read failed`. | Reconnect HDMI after boot. Use Ethernet or UART while diagnosing display output. |
| Wi-Fi AIC8801 | On 2026-11-02, scanning, DHCP and Internet traffic worked with the patched GTX driver after masking `armbian-led-state.service`. A paired failing boot showed its restore sequence pulsing GPIO38 low before SDIO wake timeout. | See the [GPIO38 findings and workaround](docs/WIFI_GPIO38_LED_RESTORE_FIX_2026-11-02.md). The pipeline includes this configuration; a new image still needs a boot test, and long-term stability remains unverified. |
| FD655 front display | Working on the tested box; packaged and enabled by the current build script. The new image packaging has not yet been verified by a full rebuild. | Check the service log and confirm `/dev/gpiochip4` lines 19/20 exist and are free. The Wi-Fi icon stays off until Wi-Fi links. |
| Bluetooth | On 2026-11-02, UART HCI power-on and a 10-second discovery scan worked after clearing the software rfkill block; Wi-Fi still passed Internet ping afterward. Pairing/audio remain untested. | See the [Wi-Fi/Bluetooth test notes](docs/WIFI_GPIO38_LED_RESTORE_FIX_2026-11-02.md). Check `rfkill`, `bluetoothctl show`, and `systemctl status h96max-bluetooth`. |
| Composite AV, analog audio, USB ports, IR, keys | Device-tree support exists, but each feature has not been fully verified. | Treat each as unverified until tested on your board. |
| Warm reboot | Has failed intermittently during Wi-Fi experiments. | If the box does not return, remove power and cold boot. Keep Ethernet and SD-card recovery available. |
| eMMC | Disabled in this test image. | Keep Android intact and boot Armbian from SD only. |

The driver built here is from a pinned AIC8800 source revision. It is **not** the exact Android module release. Android's module targets kernel 5.10 and cannot be loaded directly into this Armbian kernel. See the [driver comparison](docs/DOI_CHIEU_DRIVER_ANDROID_GOC.md) and [Wi-Fi investigation](docs/BUG_WIFI_AIC8801.md).

## Build troubleshooting

| Symptom | Check or fix |
| --- | --- |
| Firmware download or SHA-256 verification fails | Run step 2 separately, check connectivity and the pinned cache. Keep the expected hashes unchanged; do not substitute firmware from another variant. |
| Build directory has no Git checkout | Use a real clone of `armbian/build`. Keep caches separately if replacing an incomplete build directory. |
| `Docker is required` or binfmt registration fails | Install/start Docker and allow the build host to run the privileged binfmt setup. Verify `docker info`. |
| Armbian Build reports a missing package or network fetch error | Check Internet/DNS and the first failing line in the build log. Retry after restoring access. Record the upstream Armbian revision. |
| Compiler is killed or the host runs out of disk | Check `free -h` and `df -h`; reduce `H96_BUILD_THREADS` and free disk space. |
| LED service fails with `No module named gpiod` | Confirm `python3-libgpiod` was installed into the image; install it on the box and restart the service. |
| LED service fails to request GPIO lines | Check `gpioinfo`, the GPIO chip number, line ownership, and `/etc/h96-fd655.json`. Do not change pins without checking the board wiring. |
| Image boots but Wi-Fi cannot scan | This is the current known driver/SDIO problem. Use Ethernet and collect the error logs above. |

## References

- [Current board status](docs/TRANG_THAI_THUC_TE_2026-10-31.md)
- [Detailed Wi-Fi investigation](docs/BUG_WIFI_AIC8801.md)
- [Android driver comparison](docs/DOI_CHIEU_DRIVER_ANDROID_GOC.md)
- [Android boot log](logs/stock-boot.log)
- [Stock device tree](dts/original-rk3528-evb2-ddr3-v10.dts)
- [Board photos and UART locations](https://forum.armbian.com/topic/59122-h96-max-rk3528-cannot-boot-armbian-from-tfsd-card/)

Licensed under [GPL-2.0](LICENSE).
