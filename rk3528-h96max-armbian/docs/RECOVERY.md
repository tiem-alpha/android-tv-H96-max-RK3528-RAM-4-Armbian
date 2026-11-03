# Recovery and validation

Use the current [build/SD instructions](../README.md) and [radio integration](BUILD_RADIO_INTEGRATION_2026-11-02.md). The working radio baseline is the bundled GTX source/firmware with NULL/init fixes, RX preallocation and GPIO38 LED restore masked. The front-panel FD655 service is separate.

## Previously fixed initramfs boot failure (2026-10-31)

The original board-status report explicitly recorded a first-boot failure ending at `(initramfs)`. U-Boot loaded kernel/initrd, but Linux could not initialize SD controller `ffc30000.mmc` / `mmc0`. Distinguishing messages were `Busy; trying anyway`, `Timeout sending command (cmd 0x202000 ...)` and `error -110 whilst initialising SD card`. Two different cards reproduced it. The clock-update command `0x202000` was not a rootfs read failure.

Boot/rootfs existed, `e2fsck -fn` reported no filesystem damage, `rootdev` matched the rootfs UUID, and the flashed bytes matched the image. The verified recovery changed the H96 DTS `&sdmmc` block:

- Add pinctrl `normal` and `idle`, using the default SD CLK/CMD/DET/DATA0–3 groups.
- Add `no-1-8-v`, `no-sdio` and `no-mmc`.
- Remove UHS SDR12/25/50/104 properties.
- Reduce SD `max-frequency` from 50 MHz to 25 MHz; leave eMMC disabled and do not alter SD regulators.

The DTS was compiled to DTB and only `/boot/dtb/rockchip/rk3528-h96max-stock-rails-net-hdmi.dtb` on SD was replaced. No kernel rebuild or full reflash was needed for that trial. The next boot mounted `/dev/mmcblk0p2` as root and `/dev/mmcblk0p1` at `/boot`, reached login and expanded rootfs. Multiple properties changed together, so the decisive individual change was not isolated. The current image already includes this SDMMC configuration.

Historical source: `docs/TRANG_THAI_THUC_TE_2026-10-31.md` in project Git commit `2ff3dc667333f008737e3a0284b6135564f70e0a` (also present in earlier history). The full diary was removed during cleanup; this verified fix is retained here.

### Distinguish the new boot report

The subsequently reported boot already shows `mmc0: new high speed SDHC card`, `SC32G 29.7 GiB`, `mmcblk0: p1 p2`, and requested SD clock 25 MHz. It still reaches `(initramfs)`, but the supplied excerpt does not establish the same SD-initialization failure. Capture the actual root-mount error and, at the prompt, run:

```sh
cat /proc/cmdline
blkid
ls /dev/mmcblk*
```

Compare the command-line `root=` value with the detected rootfs UUID/device. Do not assume the GPT-size warning, deferred-probe message or PHY pin conflict caused the initramfs prompt without further evidence. The historical documents contain no separately verified fix based on changing root UUID, adding rootdelay or repairing GPT for this boot failure.

A separate historical boot failure involved a diagnostic service ordered before udev while waiting on journald, causing `/boot`/local-fs timeouts after roughly 112–114 seconds. Removing that service recovered boot. That was a systemd-stage ordering issue, not the early SDMMC initramfs failure; the current production image does not install the experimental observer services.

## Incident: initramfs caused by stale SD rootfs metadata (2026-11-03)

**Status:** the SD card was repaired and passed offline checks. A successful boot of the repaired card on the H96 Max has not yet been reported. This is a different failure from the October 31 SDMMC initialization issue described above.

### 1. Symptoms and initial classification

The new XFCE image booted far enough to load the kernel/initrd, enumerate the 32 GB SD card and enter the initramfs shell:

```text
mmc0: new high speed SDHC card
mmcblk0: mmc0:aaaa SC32G 29.7 GiB
mmcblk0: p1 p2
(initramfs)
```

The reported SD clock was requested 25 MHz / actual 24.9 MHz. Direct comparison with the previously bootable DTB confirmed the same SDMMC pinctrl states, voltage/UHS restrictions and regulator references. Reapplying the earlier SDMMC patch was therefore not the supported next repair.

The console also contained DRM/OPP, missing-supply, deferred-probe, Ethernet pin-conflict and GPT-size messages. Those messages alone did not establish why rootfs was unavailable. No `ALERT! UUID ... does not exist` message was captured in the supplied console excerpt; the UUID/geometry diagnosis came from inspecting the card on the development machine.

### 2. Evidence collected from the card

The card was identified as the 31,914,983,424-byte removable USB device `usb-USB_Mass_Storage_Device_817020190813-0:0`, then `/dev/sda`. Its root partition began at sector 557,056 (512-byte sectors).

| Check | Expected from the image/boot configuration | Observed on the failing card |
| --- | --- | --- |
| Root UUID | `a4964e8f-a15e-4587-aa67-91579f3afdc6` | `239f7b54-c3e8-46dd-a5c7-6353b7f6b7f7`, matching the earlier working card's filesystem |
| Root partition size | 6,441,402,368 bytes / 1,572,608 blocks of 4,096 bytes | Partition still had this size |
| Filesystem block count | 1,572,608 | Primary superblock claimed 7,643,136 blocks |
| Host kernel mount check | Filesystem fits its partition | `bad geometry: block count 7643136 exceeds size of device (1572608 blocks)` |
| Read-only fsck on card | Consistent filesystem metadata | Corrupt group-descriptor/bitmap/checksum reports under the stale primary superblock |
| Read-only fsck on original image | Clean filesystem | Passed |
| Complete root-partition comparison | Same data as the exact image | Only the first 4 KiB block differed; every remaining byte matched |

The complete comparison covered **6,441,402,368 bytes** and reported differing 4 KiB offsets `[0]`. The primary ext4 superblock lies inside that first block. The original image was:

```text
Armbian-unofficial_26.11.0-trunk_Rk3528-h96max_trixie_vendor_6.1.172_xfce_desktop.img
Size:   6,727,663,616 bytes
SHA256: ad46421c332114513e110614e612941ea87c7e88d2124f9ae4582fe6218e751a
```

The original flash had passed a full image-to-card read-back comparison before safe eject. This earlier success is important: the later stale primary metadata must not be described as a proven failure of the initial `dd` write.

### 3. Confirmed failure mechanism and unresolved origin

**Confirmed immediate cause:** the root partition contained the new image's filesystem data but its first 4 KiB block contained old primary metadata. That metadata advertised the wrong UUID and a filesystem larger than the partition. The configured root UUID could not identify that filesystem, and mounting it directly also failed the geometry check. The remaining filesystem matched the clean image; the broad fsck complaints did not establish widespread file-data corruption.

**Not established:** when or which component caused the old primary metadata to reappear after the successful flash verification. Delayed writeback, device/cache behavior, host software and card/controller faults were not isolated. They remain hypotheses, not a verified root cause. No electrical measurement or reproducible writer trace was collected.

The observed metadata inconsistency explains the failure to find/mount rootfs. It does not establish that the unrelated DRM/OPP/PHY warnings caused the initramfs shell, or that every peripheral issue is resolved.

### 4. Backup and targeted repair performed

1. Identified the exact card and inspected the root filesystem read-only. Mounted boot only with `ro,noload` to read configuration; no automatic fsck repair was accepted.
2. Saved backups outside the card under `/home/nguyentiem/h96-sd-recovery-20261103/`:
   - `partition-table.gpt`: GPT backup.
   - `disk-first-16MiB.bin`: first 16 MiB of the disk.
   - `root-first-8MiB.bin`: first 8 MiB of the root partition, including the faulty primary block.
   - `armbianEnv.txt`, `boot.cmd`, `boot.scr`, `before.dtb`: original boot files/selected DTB.
   - `rootfs-comparison.json`: complete-partition comparison result.
3. Verified the original image's rootfs with `e2fsck -fn`, then compared the complete card root partition against that exact image. The only differing 4 KiB offset was zero.
4. Unmounted both card partitions and flushed the partition-device and whole-device buffer aliases before writing.
5. Restored **only the first 4,096 bytes of `/dev/sda2`** from the matching image's root partition. The write offset was relative to the root partition, not the beginning of the disk. No generic `fsck -y`, format or full-image reflash was used.
6. Synchronized/flushed the write and verified it through both `/dev/sda2` and the equivalent whole-disk byte offset, **285,212,672**.
7. Ran read-only fsck again; it passed. Mounted root/boot read-only and checked UUIDs, `fstab`, init and radio configuration.
8. Relocated backup GPT to the physical end of the card with `sgdisk -e`, preserving partition starts, sizes and identifiers. `sgdisk -v` then reported no problems; alignment/gap advisories remained. This corrected the GPT-placement warning separately from the rootfs repair. The root partition was not manually expanded.
9. Unmounted both partitions, flushed buffers, rechecked the restored primary block, safely ejected the SD card and detached the read-only image loop device.

The 4 KiB replacement was justified by the complete comparison against this exact, clean image. It is **not a general repair recipe** for another card, image or filesystem with user changes.

### 5. What changed and what was verified

| Item | Result |
| --- | --- |
| Root primary block | Replaced 4 KiB at root-partition offset zero with the matching image block |
| Root UUID | Returned to `a4964e8f-a15e-4587-aa67-91579f3afdc6` |
| Filesystem geometry | Returned to 1,572,608 blocks, fitting the 6,441,402,368-byte partition |
| `e2fsck -fn` | Passed all five stages, exit status 0; 147,675/393,216 files and 1,222,385/1,572,608 blocks used |
| Root mount | Succeeded read-only; `/sbin/init` pointed to systemd |
| Boot/root UUID configuration | `armbianEnv.txt` and `fstab` matched actual root/boot filesystems; neither needed editing |
| Boot filesystem | Read-only check passed |
| GPT backup header/table | Moved to the card end; partition identifiers/content preserved |
| DTB/kernel/driver/firmware | No replacement needed for this repair; Wi-Fi 50 MHz and SD 25 MHz settings retained |
| GPIO38/FD655/Bluetooth | Bundled radio metadata and enabled-service configuration remained present; this was not a runtime radio test |
| Android/eMMC | Not modified |
| Final state | Card unmounted and safely ejected; hardware boot confirmation pending |

### 6. Next checks and prevention

Cold boot the box with the repaired SD. Confirm `findmnt /` points to the SD root partition, systemd reaches userspace, and UUIDs match. Then test Wi-Fi/DHCP/traffic through `wlan0`, FD655 date/time/icons and Bluetooth. A successful host mount is not proof of a successful hardware boot.

For future flashes, identify/unmount every target partition, retain whole-image checksum/read-back verification, and also check the on-card filesystem UUID/geometry against the image before boot. Flush partition and whole-device aliases and eject safely. If this recurs, inspect the primary metadata after reconnecting the reader and after each boot to localize when it changes; only then investigate a specific writer/cache/device cause.

For another initramfs failure, collect `/proc/cmdline`, `blkid`, device nodes and the actual mount error before choosing a fix. Preserve this incident analysis even when routine build logs and superseded notes are removed.

## Keep a working SD recovery route

Before replacing a bootable card's kernel, DTB or modules, save its active boot configuration, selected DTB, installed modules and matching firmware outside the box. Record hashes and the kernel version. Keep the card accessible from a development computer and retain Ethernet/UART access.

If a new image fails, use the previously working SD or restore its matching backup. Do not combine modules from different kernels or select an old experimental pair just because filenames match. Restoring files on disk takes effect after a subsequent boot; do not hot-unbind/rebind SDIO to force recovery. Earlier trials caused stuck SDIO and an Oops during re-probe.

If SSH is unavailable, power off and attach SD to a computer. Identify its actual root/boot partitions, restore the backed-up boot configuration and matching files, synchronize and unmount safely, then cold boot. Rebuild module dependencies with `depmod` in a compatible environment when modules change. Preserve UUID/PARTUUID references when restoring boot files.

## Read-only checks after boot

```sh
uname -r
findmnt /
findmnt /boot
cat /boot/armbianEnv.txt
cat /etc/h96-radio-build.conf
modinfo -n aic8800_bsp
modinfo -n aic8800_fdrv
systemctl is-enabled armbian-led-state.service
systemctl status h96-fd655.service h96max-bluetooth.service --no-pager
nmcli device status
nmcli device wifi list
rfkill list
```

LED restore should be `masked`. Do not change `pwr-wifi` trigger/brightness while validating Wi-Fi; its GPIO38 pulse was implicated by the paired-boot test. FD655 uses GPIO4 lines 20/19 and should remain enabled. Verify Wi-Fi DHCP and traffic explicitly over `wlan0`, plus date/time/icons and Bluetooth separately.

Do not load Android kernel 5.10 modules into Armbian kernel 6.1. Android comparison evidence remains under `evidence/android-192.168.0.4/`. Old trial deployment scripts require dated on-box packages/backups and are not current recovery installers.

## eMMC remains a separate task

The current DTB disables eMMC; no eMMC installation has been validated. An earlier `emmc-enabled-from-baseline.dtb` was only prepared, then postponed and reverted on SD. Do not apply it without comparing against the current baseline. Follow the [SD-to-eMMC plan](SD_TO_EMMC_INSTALLATION.md): identify hardware, back up Android, establish USB recovery and verify a boot method before writing eMMC.
