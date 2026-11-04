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

The image builds the bundled source in `patches/vendor/aic8800/driver` (no driver Git fetch during build), originally taken from `gtxaspec/aic8800-wifi` at commit `a870f7f15170a5899bf0b98769896fd1a7d4bf1e`, generic `SDIO/driver_fw/driver/aic8800`, with the kernel 6.1/init-guard fixes already applied directly to the bundled source. RX preallocation and SDIO power control are enabled, and the SDIO clock is 50 MHz. The build masks `armbian-led-state.service` to prevent the GPIO38 pulse found in the paired boot traces.

`build-desktop.sh` verifies all 13 bundled firmware files against SHA-256 and stages them into the image overlay. No Wi-Fi Git checkout or network download is needed. To check separately:

```bash
bash tools/prepare-aic8800-gtx.sh
```

Driver and firmware live in `patches/vendor/aic8800/`. Edit the driver there; source hashes participate in the kernel cache key. `H96_AIC_SOURCE_DIR` is no longer used.

## 3. Build the image

Use the existing complete Armbian source tree in `armbian-build/`; framework `.git` metadata is not required. The script checks the tree, stages board/driver/firmware/LED inputs, and records a content SHA-256 instead of querying a framework commit. It does not initialize or clone a framework repository.

```bash
# Prepare/check local inputs without Docker or compilation:
H96_PREPARE_ONLY=yes ./build-desktop.sh
# Build when disk space and dependencies are ready:
H96_BUILD_THREADS=8 ./build-desktop.sh
# Reuse an existing Docker base without an age-triggered refresh:
H96_DOCKER_LOCAL_BASE=yes H96_BUILD_THREADS=8 ./build-desktop.sh
```

The H96 kernel baseline is pinned to commit `4ee92c1e3bd78ddc6f57c5a9dc056281ea863072` (6.1.172). Six empty userpatch overrides skip changes already present in that commit; see their README before updating the kernel.

The local snapshot adapter suppresses framework Git log queries without `.git`, and `GIT_CEILING_DIRECTORIES` prevents source-cache Git commands from discovering the enclosing project repo. This does **not** remove Armbian's internal Git dependency for kernel/U-Boot and other fetched sources, and does not guarantee an offline build. Those source caches must remain valid; missing dependencies may still require network access. Do not delete cache Git metadata.

Choose a smaller positive `H96_BUILD_THREADS` value if the host has limited RAM. Firmware and LED files are checked before starting Armbian Build. It selects:

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

The [radio integration notes](docs/BUILD_RADIO_INTEGRATION_2026-11-02.md) describe the pinned source, firmware checks, GPIO38 fix and component validation. The November 3 full XFCE image built successfully and passed SHA-256 plus read-only image inspection for Wi-Fi firmware/modules, GPIO38 masking, Bluetooth, FD655 and desktop packages. A boot test on the box is still required.

```bash
find armbian-build/output/images -maxdepth 1 -type f \( -name '*.img' -o -name '*.img.xz' -o -name '*.img.gz' \) -printf '%f\n'
```

Armbian's upstream `build` branch can change. This repository does not pin an upstream Armbian commit, so a future fresh clone may need compatibility fixes. Keep the local input SHA-256 from `armbian-build/config/h96-local-build.conf` and the build log when reporting a failure.

## 4. Write the image to an SD card

Old images may be retained as `.img.gz`; use `gzip -dc` instead of `xzcat` for that format. Existing image checksums apply to the decompressed bytes.

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
sudo dd if="$image_path" of="$sd_device" bs=16M oflag=direct conv=fsync status= 
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

The FD655 service shows `DD/MM` for 15 seconds and `HH:MM` for 45 seconds. The Ethernet and Wi-Fi icons follow each interface's link state. Change timing, brightness, or display mapping in `/etc/h96-fd655.json`, then run `sudo systemctl restart h96-fd655.service`. The program expects GPIO4 at `/dev/gpiochip4`, with line 20 for clock and line 19 for data. See [LED details](led/README.md).

## Known problems and limits

| Component | Current status | What to do |
| --- | --- | --- |
| SD boot and root filesystem | Booted on the tested box after the SD controller device-tree fix. | If boot stops at initramfs with `mmc` timeout or `-110`, confirm the image includes the current DTS and try another SD card. Read the UART log before changing bootloader settings. |
| Ethernet | Working on the tested box. | Check `ip -br addr`, the cable, and DHCP if SSH is unavailable. |
| HDMI | Picture may appear only after unplugging and reconnecting HDMI. Logs have shown `ddc read failed`. | Reconnect HDMI after boot. Use Ethernet or UART while diagnosing display output. |
| Wi-Fi AIC8801 | On 2026-11-02, scanning, DHCP and Internet traffic worked with the patched GTX driver after masking `armbian-led-state.service`. A paired failing boot showed its restore sequence pulsing GPIO38 low before SDIO wake timeout. | See the [GPIO38 findings and workaround](docs/WIFI_GPIO38_LED_RESTORE_FIX_2026-11-02.md). The pipeline includes this configuration; a new image still needs a boot test, and long-term stability remains unverified. |
| FD655 front display | Working on the tested box; packaged and enabled by the current build script. Packaging was verified in the rebuilt November 3 image; hardware validation of that image remains pending. | Check the service log and confirm `/dev/gpiochip4` lines 19/20 exist and are free. The Wi-Fi icon stays off until Wi-Fi links. |
| Bluetooth | On 2026-11-02, UART HCI power-on and a 10-second discovery scan worked after clearing the software rfkill block; Wi-Fi still passed Internet ping afterward. Pairing/audio remain untested. | See the [Wi-Fi/Bluetooth test notes](docs/WIFI_GPIO38_LED_RESTORE_FIX_2026-11-02.md). Check `rfkill`, `bluetoothctl show`, and `systemctl status h96max-bluetooth`. |
| Composite AV, analog audio, USB ports, IR, keys | Device-tree support exists, but each feature has not been fully verified. | Treat each as unverified until tested on your board. |
| Warm reboot | Has failed intermittently during Wi-Fi experiments. | If the box does not return, remove power and cold boot. Keep Ethernet and SD-card recovery available. |
| eMMC | Disabled in this test image. | Keep Android intact and boot Armbian from SD only. |

The driver built here is from a pinned AIC8800 source revision. It is **not** the exact Android module release. Android's module targets kernel 5.10 and cannot be loaded directly into this Armbian kernel. See the [radio integration notes](docs/BUILD_RADIO_INTEGRATION_2026-11-02.md) and [recovery guide](docs/RECOVERY.md).

## Build troubleshooting

| Symptom | Check or fix |
| --- | --- |
| Bundled firmware is missing or SHA-256 verification fails | Run step 2 separately and restore the complete bundled firmware set. Keep expected hashes unchanged; do not substitute another variant. |
| Local framework tree is incomplete | Restore the missing source files named by the adapter. Framework `.git` is optional; internal kernel/U-Boot cache metadata is separate. |
| `Docker is required` or binfmt registration fails | Install/start Docker and allow the build host to run the privileged binfmt setup. Verify `docker info`. |
| Armbian Build reports a missing package or network fetch error | Check Internet/DNS and the first failing line in the build log. Retry after restoring access. Record the local build input SHA-256. |
| Compiler is killed or the host runs out of disk | Check `free -h` and `df -h`; reduce `H96_BUILD_THREADS` and free disk space. |
| LED service fails with `No module named gpiod` | Confirm `python3-libgpiod` was installed into the image; install it on the box and restart the service. |
| LED service fails to request GPIO lines | Check `gpioinfo`, the GPIO chip number, line ownership, and `/etc/h96-fd655.json`. Do not change pins without checking the board wiring. |
| Image boots but Wi-Fi cannot scan | Confirm GTX modules/firmware, GPIO38 LED-restore masking and the H96 DTB, then collect kernel/NetworkManager logs over Ethernet. |

## References

- [Documentation index](docs/README.md)
- [Recovery guide and initramfs incident analysis](docs/RECOVERY.md)
- [Maintained tools](tools/README.md)
- [Prebuild review and cleanup](docs/PREBUILD_CHECK_2026-11-03.md)

- [SD-to-eMMC installation plan (not yet validated)](docs/SD_TO_EMMC_INSTALLATION.md)
- [Stock device tree](dts/original-rk3528-evb2-ddr3-v10.dts)
- [Board photos and UART locations](https://forum.armbian.com/topic/59122-h96-max-rk3528-cannot-boot-armbian-from-tfsd-card/)

Licensed under [GPL-2.0](LICENSE).
