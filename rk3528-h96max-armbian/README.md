# H96 Max RK3528 Armbian image

This repository builds a Debian Trixie XFCE image for the H96 Max RK3528 box used in this project. The image includes the H96 Max device tree, vendor kernel, SD boot support, Ethernet, HDMI configuration, AIC8801 Wi-Fi modules and firmware, Bluetooth setup, and the FD655 front-panel clock and network indicators.

**A successful build does not mean every device works.** This box boots from SD and Ethernet works. The FD655 display works on the tested box. Wi-Fi is detected but currently fails to scan or connect reliably. Other limitations appear below.

The board name alone does not identify the hardware. Check that your box uses RK3528 and that its Wi-Fi device is SDIO `5449:0145` before using this image. The Android device tree calls the Wi-Fi chip `ap6275s`, but the live device and Android driver identify AIC8801.

## 1. Get the repository and tools

Use a Linux build host with Internet access, Git, Python 3, ADB, Docker, and enough free space for an Armbian build. Docker must be running. On an x86-64 host, the build script uses a privileged Docker container to register ARM64 QEMU/binfmt. Armbian Build may request host packages or root privileges during its first run.

```bash
sudo apt update
sudo apt install -y git python3 adb docker.io xz-utils util-linux
sudo systemctl enable --now docker

git clone https://github.com/tiem-alpha/android-tv-H96-max-RK3528-RAM-4-Armbian.git
cd android-tv-H96-max-RK3528-RAM-4-Armbian/rk3528-h96max-armbian
```

If your clone has a different directory name, enter its `rk3528-h96max-armbian` directory. Run all remaining build commands from that directory. Confirm the build files are present:

```bash
ls -l build-desktop.sh patches/config/boards/rk3528-h96max.csc led/h96-fd655.py
```

## 2. Get the factory Wi-Fi firmware

**This is required for a complete image.** Firmware copied from the tested box is excluded from Git. A fresh clone cannot build the Wi-Fi-enabled image until you provide these files. Use the original Android installation on the *same box*, with ADB enabled and `su 0` access:

```bash
adb devices -l
adb shell 'su 0 cat /sys/bus/sdio/devices/*/modalias'
python3 tools/capture-aic-firmware.py
```

The modalias should identify vendor `5449` and device `0145`. The capture script writes to `patches/userpatches/overlay/lib/firmware/aic8800/SDIO/aic8800D80/`. Check the files required by the current build:

```bash
firmware_dir=patches/userpatches/overlay/lib/firmware/aic8800/SDIO/aic8800D80
for file in fw_adid.bin fw_patch.bin fw_patch_table.bin fmacfw.bin aic_userconfig.txt; do
    test -s "$firmware_dir/$file" && echo "OK $file" || echo "MISSING $file"
done
```

If you already saved the firmware from this same box, copy it into that directory instead. Do not rename another chip's firmware to satisfy the build check. If `adb devices` shows no device, enable USB debugging and authorize the host in Android. If `su 0` fails, the script cannot read the factory files; obtain a valid backup before building.

## 3. Build the image

Clone Armbian Build *inside this directory*. Use the existing checkout if one is already present. The script copies the current board files, patches, firmware overlay, and LED files into that checkout before every build.

```bash
git clone --depth=1 https://github.com/armbian/build.git armbian-build
H96_BUILD_THREADS=8 ./build-desktop.sh
```

Choose a smaller positive `H96_BUILD_THREADS` value if the host has limited RAM. The script checks the firmware and LED files before starting Armbian Build. It selects:

| Setting | Value |
| --- | --- |
| Board | `rk3528-h96max` |
| Kernel branch | `vendor` (Rockchip 6.1 family) |
| Distribution | Debian `trixie` |
| Image | XFCE desktop, mid tier, non-minimal |
| Boot device tree | `rockchip/rk3528-h96max-stock-rails-net-hdmi.dtb` |
| Wi-Fi | AIC8800-family modules for the AIC8801 SDIO device |
| FD655 display | Python program, configuration, `python3-libgpiod`, enabled systemd service |

The build result is under `armbian-build/output/images/`. Use the filename actually produced on your host:

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
ls /lib/firmware/aic8800/SDIO/aic8800D80/
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
| Wi-Fi AIC8801 | SDIO `5449:0145` and `wlan0` can appear, but scanning and connection are unreliable. Logs show SDIO wake failure and CMD52 timeout `-110`. | Use Ethernet. Check `dmesg`, `journalctl -u NetworkManager`, and `iw dev wlan0 scan`. A password, DHCP, or static IP change does not fix a failed scan. Do not assume a driver with the same version number solves this. |
| FD655 front display | Working on the tested box; packaged and enabled by the current build script. The new image packaging has not yet been verified by a full rebuild. | Check the service log and confirm `/dev/gpiochip4` lines 19/20 exist and are free. The Wi-Fi icon stays off until Wi-Fi links. |
| Bluetooth | Configured but not fully verified on Linux. | Check `systemctl status h96max-bluetooth` and `bluetoothctl list`; collect logs before changing UART or firmware settings. |
| Composite AV, analog audio, USB ports, IR, keys | Device-tree support exists, but each feature has not been fully verified. | Treat each as unverified until tested on your board. |
| Warm reboot | Has failed intermittently during Wi-Fi experiments. | If the box does not return, remove power and cold boot. Keep Ethernet and SD-card recovery available. |
| eMMC | Disabled in this test image. | Keep Android intact and boot Armbian from SD only. |

The driver built here is from a pinned AIC8800 source revision. It is **not** the exact Android module release. Android's module targets kernel 5.10 and cannot be loaded directly into this Armbian kernel. See the [driver comparison](docs/DOI_CHIEU_DRIVER_ANDROID_GOC.md) and [Wi-Fi investigation](docs/BUG_WIFI_AIC8801.md).

## Build troubleshooting

| Symptom | Check or fix |
| --- | --- |
| `Missing ... firmware` before build | Complete step 2. Check that all five required files are nonempty in the specified directory. |
| `adb: no devices` or `su` fails | Boot Android, enable USB debugging, authorize ADB, and confirm root access. Restore firmware from a backup if Android is unavailable. |
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
