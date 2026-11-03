# Prebuild review — 2026-11-03

The SD image configuration contains the main required components. This review does not establish that a new image has booted. It does not apply the latest fixes retroactively to the XFCE image built on October 31.

| Component | Review result |
| --- | --- |
| Debian Trixie/XFCE | Desktop XFCE, mid tier selected |
| Board/kernel/DTB | Hinlink HT2 baseline, vendor RK35xx, H96 stock-rails-net-hdmi DTB; SD 25 MHz; eMMC disabled |
| Wi-Fi | Bundled source with NULL/init fixes; kernel module configuration and RX preallocation; no Wi-Fi Git fetch |
| Firmware | All 13 SHA-256 checks pass |
| GPIO38 | Post-image hook masks `armbian-led-state.service` |
| Wi-Fi autoload | BSP before FDRV through modules-load and softdep |
| Bluetooth | BlueZ/rfkill packages; UART2 1.5 Mbaud service; unblock and AutoEnable |
| FD655 | Program/config/service, python3-libgpiod dependency, enabled unit; date 15 s/time 45 s; CLK20/DAT19 |
| Ethernet/HDMI | DTS configuration present; needs fresh-image hardware validation |
| eMMC | Disabled; installation plan remains unvalidated |

## Component checks

The kernel hook ran twice in isolated staging without duplicate Kconfig/Makefile entries. Copied source matched the bundle except for intentional Kconfig path changes. The post-image hook ran twice on a temporary rootfs with a minimal fake BlueZ unit and `systemctl --root`, without starting services. Firmware, masking, module autoload, Bluetooth service and AutoEnable passed; this does not verify actual BlueZ package installation. Shell/Python/JSON syntax passed. FD655 program defaults and README were corrected to match the tested JSON pin mapping.

Local preparation passed with Git invocation blocked and produced the same input SHA-256 twice. The framework `.git` requirement was removed; internal kernel/U-Boot Git caches remain necessary. The adapter rejects incomplete framework source trees.

## Cleanup and actual build findings

- Initial disk space was approximately 16 GiB; available RAM approximately 11 GiB with 4 GiB swap. No forced memory-cache dropping was needed.
- `make ARCH=arm64 clean` removed old kernel build products while retaining source/config. Root-owned files required repeating the clean with sudo; it completed.
- All four old images were compressed to `.img.gz`. Each original was removed only after its SHA-256 matched the decompressed data. Existing checksum files remain useful after decompression. Free space increased to approximately 31 GiB. Kernel/U-Boot Git metadata, source caches and unrelated application caches were preserved.
- Armbian Docker does not mount arbitrary top-level vendor directories. The launcher now stages the bundled driver in `userpatches/h96-vendor/aic8800/driver`; all 135 staged source files matched the bundle.
- The first compiling attempt rejected six framework patches. Complete reverse dry-runs against kernel commit `4ee92c1e3bd78ddc6f57c5a9dc056281ea863072` passed for all six, proving those changes were already present. Empty userpatch overrides skip only these duplicates, and the extension pins that kernel commit. Patch errors are not globally ignored.
- A compiled DTB exposed an inherited 200 MHz SDIO maximum. The H96 DTS now explicitly caps Wi-Fi SDIO at 50 MHz, matching the driver's tested setting; the build was restarted with this input. The SD controller is separately capped at 25 MHz.
- `H96_DOCKER_LOCAL_BASE=yes` uses the existing Docker base instead of forcing an update solely because its age marker expired. Missing bases and other dependencies may still need network access.

Current command:

```sh
H96_DOCKER_LOCAL_BASE=yes H96_BUILD_THREADS=8 ./build-desktop.sh
```

Latest build log: `logs/build-2026-11-03-sdio50.log`. Superseded logs from stopped attempts were removed after the relevant fixes were documented. Documentation/tool cleanup while this build runs changes repository documentation and archived tools only; it does not restage inputs into the active Armbian tree.

## Remaining verification

After the build: verify image checksum, inspect partitions/rootfs and confirm modules, firmware, DTB, services and XFCE are present. Then boot SD on the box and test cold boot/reboot, Wi-Fi/DHCP/traffic, Bluetooth and FD655/system time. The initial prebuild review did not write SD/eMMC; the later SD flash is recorded below.

## Completed image validation

The full XFCE build completed successfully on 2026-11-03 at approximately 09:07 local time (framework runtime 51:02). Output: `armbian-build/output/images/Armbian-unofficial_26.11.0-trunk_Rk3528-h96max_trixie_vendor_6.1.172_xfce_desktop.img`, 6,727,663,616 bytes (6.27 GiB).

The generated SHA-256 check passed. Both partitions were mounted read-only with journal replay disabled, inspected, then unmounted and the loop device detached. Verified all 13 firmware hashes, BSP/FDRV/BTLPM modules, BSP-before-FDRV autoload, GPIO38 LED-restore mask, enabled FD655/Bluetooth units, FD655 CLK20/DAT19 and date/time timings, BlueZ AutoEnable/unblock, and installed python3-libgpiod/BlueZ/rfkill/XFCE/NetworkManager packages. The image DTB reports Wi-Fi SDIO 50 MHz, SD 25 MHz and eMMC disabled. Boot/root UUID references match the image partitions.

The SD flashing result is recorded below. On-box boot, Wi-Fi after reboot, Bluetooth and FD655 still need hardware validation of this new image.

## SD card flashed and verified

At the user's request, the verified image was written to the 31,914,983,424-byte removable USB SD card identified by `usb-USB_Mass_Storage_Device_817020190813-0:0` (then `/dev/sda`). Existing partitions were unmounted before writing. Image SHA-256 was checked again. Direct/fsync writing completed for all 6,727,663,616 bytes, then read-back `cmp` matched every image byte after flushing device buffers. The card was safely ejected. Android/eMMC was not modified. Hardware boot testing is still pending.

## First boot issue and targeted SD recovery

The box reached initramfs. Inspection later found the card's primary rootfs superblock carried the old UUID/geometry, although the image itself was clean and the SDMMC fix was present. Full partition comparison localized the difference to its first 4 KiB. The backed-up block was restored from the exact verified image; fsck passed, root mounted and its UUID matched boot/fstab. Backup GPT was moved to the card end and the card safely ejected. See [the recovery record](RECOVERY.md) for evidence and limitations. The cause of the later primary-superblock change is unproven; a successful hardware boot after repair is still pending.
