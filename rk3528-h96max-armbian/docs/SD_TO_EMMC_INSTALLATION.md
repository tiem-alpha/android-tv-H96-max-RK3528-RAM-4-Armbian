# Installing Armbian from SD onto eMMC — H96 Max RK3528

Updated 2026-11-03. SD boot and eMMC detection have now been verified on the project box. The user explicitly authorized overwriting Android and skipping its backup. Installation and readback checks passed, but cold boot now fails, including with SD inserted. SPL crashes before loading U-Boot proper. See the incident analysis below.

## Starting state

- The repaired November 3 image boots from SD, rootfs expanded to the 32 GB card, and Ethernet/Wi-Fi connect. The generic image DTB disables eMMC; the on-box candidate enables it.
- `emmc-enabled-from-baseline.dtb` was previously prepared, but installation was postponed and the SD DTB restored to baseline. eMMC has not been written. See the [recovery guide](RECOVERY.md).
- Patched GTX Wi-Fi and the FD655 date/time display have worked on the box. Wi-Fi source and all matching firmware are bundled in `patches/vendor/aic8800`; NULL/init fixes are applied directly. The build does not fetch the Wi-Fi driver from Git. Both features are integrated into the pipeline, but a complete rebuilt image still needs hardware validation.
- The installed U-Boot payloads match the bootable SD byte-for-byte. Its configuration and embedded DTB support eMMC and SD. This is preflight evidence; standalone eMMC boot still requires a hardware test. This procedure uses the dedicated installer, not a blind SD clone or generic `armbian-install`.

## Step 1 — Record the running SD system

Run these read-only commands on the box and save the output on the development machine:

```sh
uname -a
findmnt /
findmnt /boot
lsblk -o NAME,PATH,SIZE,TYPE,FSTYPE,MODEL,MOUNTPOINTS
cat /boot/armbianEnv.txt
cat /proc/cmdline
```

**Checkpoint:** identify the SD device, root/boot partitions, selected DTB and kernel version. Do not identify SD/eMMC solely by `mmcblk0` or `mmcblk1`; numbering can change when eMMC is enabled.

## Step 2 — Enable eMMC detection while booting from SD

1. Back up the active DTB and `armbianEnv.txt`, record checksums and keep copies outside the box for recovery with an SD reader.
2. Compare the eMMC node with the original Android DTS: pinctrl, bus width, clocks, regulators and related properties. Recheck the earlier candidate against the current baseline before using it.
3. Create a DTB candidate with only the necessary eMMC changes. Retain working SD, Wi-Fi and display settings.
4. Boot from SD with the candidate and inspect `lsblk`, MMC information and kernel logs.

**Checkpoint:** root/boot still reside on SD; eMMC reports the expected capacity without I/O errors/timeouts. Do not format, mount writable, change partitions or write a bootloader to eMMC at this stage. Restore the DTB with a computer if boot fails.

## Step 3 — Back up Android/eMMC and establish recovery

1. Identify eMMC using hardware information and its partition layout.
2. Back up the entire eMMC user area to an external drive or development machine with sufficient free space. Record size/SHA-256 and verify the backup can be read.
3. Check for `boot0`/`boot1`; back them up separately if present and record the relevant boot configuration. Do not change boot selection or write protection.
4. Save the partition table, MMC information and available boot logs.
5. Verify Loader/MaskROM access over USB for this exact board, compatible tools/loader and a concrete restore method. Do not erase eMMC merely to test recovery mode.

**Checkpoint:** a readable, checksummed backup exists outside eMMC and a specific recovery procedure is available. Write actual backup commands only after the device has been identified; do not execute commands using guessed device names.

## Step 4 — Choose the boot method and prepare the target system

1. Inspect the box's BootROM/SPL/U-Boot chain and eMMC boot support. Choose between retaining the stock bootloader and a verified compatible replacement.
2. Specify partitions, bootloader locations, kernel/DTB loading and rootfs identification. Distinguish an eMMC rootfs that still needs SD from independent eMMC boot; the final goal is to boot with SD removed.
3. Prepare an image or install payload with eMMC-enabled DTB, matching Wi-Fi modules/firmware, masked LED-restore service and enabled FD655 service.
4. Test the prepared system on SD first: Wi-Fi scanning, DHCP and traffic, plus alternating `DD/MM` and `HH:MM` display.

**Checkpoint:** a concrete install procedure names the exact devices, regions, image and checksum. Do not run `armbian-install` or copy the SD image to eMMC before completing the preceding checks.

## Step 5 — Install using the verified method

This step may erase Android. Recheck backups and the target device before executing the commands prepared in step 4.

- Write bootloader, partitions and rootfs according to the selected layout.
- Update UUID/PARTUUID references in boot configuration and `fstab` from actual target partitions; avoid duplicated identifiers after cloning SD.
- Verify written data, DTB, modules, firmware and services; synchronize data before shutdown.

**Checkpoint:** retain installation logs and verification results. A successful rootfs copy does not prove eMMC boot works.

## Step 6 — Verify independent eMMC boot

1. Power off completely, remove SD and power on.
2. Confirm rootfs and boot partitions reside on eMMC as designed; collect UART logs if boot fails.
3. Test Ethernet, HDMI, Wi-Fi scanning/association/DHCP/traffic explicitly through `wlan0`, FD655 date/time and network icons. Check timezone and time synchronization.
4. Test Bluetooth if needed, then repeat cold boots and reboots, recording each result.
5. Retain the rescue SD and Android backup until the system is confirmed stable.

**Complete when:** the box boots without SD, rootfs runs on eMMC, and Wi-Fi/display checks pass after restarting.

## Progress log

| Step | Status | Evidence |
| --- | --- | --- |
| 1. Record SD system | Complete | SSH as tiem; root mmcblk0p2, boot mmcblk0p1 |
| 2. Detect eMMC | Complete | mmcblk1, MMC CWBD3R, 62,537,072,640 bytes; HS400 Enhanced Strobe |
| 3. Android backup | Explicitly waived by user | SD rescue system retained; Android overwrite authorized |
| 4. Select boot/install method | Static preflight complete | Matching SPL/FIT; eMMC enabled in embedded U-Boot DTB |
| 5. Write eMMC | Complete | Checksum copy, filesystem checks, and fresh SPL/FIT readback passed |
| 6. Boot without SD | Not performed | — |

## Current device and bootloader evidence

Linux identifies the source as `/dev/mmcblk0` (SD, 31,914,983,424 bytes) and target as `/dev/mmcblk1` (MMC CWBD3R, 62,537,072,640 bytes, CID `150100435742443352009bfe51d35200`). U-Boot aliases differ from Linux numbering: its `mmc0` is eMMC at ffbf0000 and `mmc1` is SD at ffc30000. Do not equate U-Boot indices with Linux device suffixes.

The candidate DTB differs from the bootable SD DTB only in eMMC `status=okay`. SD remains 25 MHz and Wi-Fi 50 MHz. Boot configuration/DTBs are saved on the box at `/var/backups/h96-emmc-detect-20261103` and outside the box at `/home/nguyentiem/h96-emmc-detect-20261103`.

| Payload | User-area sector (512 bytes) | Size | SHA-256 matching the bootable SD |
| --- | --- | --- | --- |
| idbloader.img | 64 | 311,296 bytes | `33141f9180217ab259c79fafcab09f2ed65c4e10bba5685f6f7d9bfc56fe68be` |
| u-boot.itb | 16,384 | 1,313,280 bytes | `59f9e32c4ef73eda1cee620ca9c8e3644e6960483d04f2382fee3b510fcc5932` |

The vendor U-Boot configuration has MMC DW/SDHCI Rockchip, GPT/ext4 and distro boot enabled, with environment stored nowhere. Its FIT's embedded DTB enables both controllers; its boot-target order tries SD before eMMC. No write to eMMC boot0/boot1 or EXT_CSD boot-selection settings is planned. Standard split-loader offsets are also documented by [U-Boot](https://docs.u-boot.org/en/stable/board/rockchip/rockchip.html).

## Dedicated on-box installer

`tools/install-emmc.py` is specific to this verified board/device pair. Run it only on the box while root and boot are on the identified SD. With only `--expect-cid`, it performs read-only eMMC preflight; installation additionally requires explicit `--erase-android --no-android-backup` flags. The Android backup requirement above is intentionally waived for this authorized run.

The installer checks CID, type, capacity, mounts, source bootloader bytes, bootloader configuration/embedded DTB and radio DT settings. It creates unique eMMC filesystem UUIDs, a 512 MiB boot partition at sector 32,768 and a remaining-space rootfs. It copies the running system with two rsync passes (the second checks file content), preserves ownership/ACLs/xattrs, installs an eMMC-enabled DTB and rewrites only target boot/fstab UUID entries. The SD boot configuration is preserved.

After copying, it checks firmware/module/kernel/initrd hashes, service links and both filesystems offline. Only then does it clear the unallocated loader gap and write/read-back the verified SPL/FIT payloads. It checks UUIDs and files again after flushing partition/whole-device aliases. The temporary detection read-only rule is removed from the installed eMMC system; the SD rescue rule is restored afterward.

State/logs on SD: `/var/lib/h96-emmc-install/state.json`, `preflight.json`, and `install.log`. An initial tree-parsing guard stopped after GPT creation and before formatting. The root cause was lsblk JSON without explicit tree output; the code now requests `--tree`, validates actual partition paths/sizes and only permits a constrained resume of that specific pre-format stop. Source SD remained running throughout.

### Completed installation verification (2026-11-03)

Android was overwritten without a backup, as explicitly authorized. Both target filesystems passed checks; fresh bootloader readback matched the preflight hashes. Target boot configuration, GPIO38 service mask, eMMC DTB, radio files, and distinct filesystem UUIDs were verified. The target was unmounted afterward; the running system remains on SD.

- eMMC root UUID: `d7397e6b-f9b5-4cef-9b4e-b25abab11d1e`
- eMMC boot UUID: `2153a1bf-4e51-4d32-ad48-fa5de4671fd4`
- Independent report: `/home/nguyentiem/h96-emmc-install-20261103/verification.json` on the workstation.
- Remaining validation: power off, remove SD, power on, then confirm the root UUID and radio/display operation over SSH. Installation checks do not establish independent boot success.

## Cold-boot failure: SPL abort (2026-11-03)

The user reports boot failure after the eMMC write and power cycle. Inserting SD does not recover boot.

A bootable SD rootfs does not prove its embedded bootloader executed. The previous claim that the SD bootloader was hardware-tested is withdrawn. Android's eMMC bootloader may have loaded the SD system. That previous boot chain remains unverified.

### Confirmed UART evidence

The user supplies readable DDR and SPL output. DDR firmware v1.09 identifies DDR3, 4096 MB. It prints training results at 1056 MHz and exits. This does not prove RAM stability.

SPL then prints `U-Boot SPL board init` and aborts:

```text
Synchronous Abort, ESR 0x96000004
PC 0x9410, LR 0xe4f8
x0 = x4 = 0x0000300000027e6f
x23 = 0x39a58, x24 = 0x31258
```

The exact retained SPL ELF maps PC to `strcmp`, `lib/string.c:189`. LR maps to `driver_check_compatible`, inlined into `lists_bind_fdt`, `drivers/core/lists.c:116,167`. The failing instruction reads the first byte through x4. This is an invalid non-NULL pointer.

The driver at 0x39a58 is `rockchip_sfc_driver`. Its match table starts at 0x31258. The on-disk pointer there is 0x28e6f, pointing to `rockchip,fspi`. The runtime register contains a different, invalid value. This supports investigating SPL runtime data corruption, DDR stability, or writes overlapping SPL data. It does not identify the original corrupting operation. Adding a NULL guard to strcmp cannot fix this invalid non-NULL pointer.

### Binary and configuration checks

- The retained SPL binary occurs exactly at byte 63488 inside the installed idbloader payload.
- SPL SHA256: `6addd3cc424a94271e17a846a4a11752660ebca60cdae1e631357d59cff1d5ca`.
- DDR blob `rk3528_ddr_1056MHz_v1.09.bin` occurs exactly at byte 2048 inside idbloader.
- idbloader and FIT match the retained build outputs and installation readback hashes.
- idbloader uses sector 64. FIT uses sector 16384. Both match the package installer. SPL expects FIT at sector 0x4000.
- The configured board is inherited from Hinlink HT2; U-Boot DT model/configuration is Hinlink H28K. It is not a validated H96-specific loader.
- SPL/U-Boot SD max-frequency is 150 MHz. The tested Linux board configuration limits SD to 25 MHz. This is a separate unvalidated difference, not the demonstrated crash cause.
- U-Boot DT stdout references UART2, while DEBUG_UART_ALWAYS selects UART0 at 0xff9f0000. Source serial-uclass excludes normal console selection with this option. The DT discrepancy alone does not prove lost console output.

### Recovery and next validation

Do not change offsets without evidence. Do not flash another loader before establishing recovery access. First obtain USB Loader/MaskROM access or an explicitly identified board recovery mechanism. Preserve current boot data and logs. A replacement loader must be tested with captured DDR/SPL/U-Boot output. A lower DDR frequency is a diagnostic candidate, not a confirmed repair.

Raw logic captures remain on the workstation under `/home/nguyentiem/h96-emmc-install-20261103/`. Raw captures have bit errors; the readable user-supplied UART trace establishes the abort above.

### Changes after the SPL audit

`tools/install-emmc.py` now rejects installation and resume before accessing devices. Read-only preflight remains available. Four non-destructive regression checks pass, including rejection before preflight/device access. Do not use an old deployed copy of this installer.

`tools/prepare-ddr-diagnostic.py` reproduces the audited baseline loader exactly before changing any parameters. The diagnostic changes only DDR3 frequency from 1056 to 528 MHz. The tool exports and compares all DDR parameters, checks unchanged SPL content/location and leaves the source blob unchanged. It writes ordinary files only.

Prepared diagnostic: `/home/nguyentiem/h96-emmc-install-20261103/ddr528-verified-package/`. Candidate SHA256: `4ac81678a581ab0fa58233e76cf4e645fc16c84f0f4e18f9cbdf7b2953ca11db`. The package remains UNVALIDATED and has not been flashed. This is a DDR diagnostic, not proof of a repaired boot chain.

The parameter tool is Rockchip ddrbin_tool v1.19, already available in the local Luckfox rkbin checkout. Its hash and both DDR hashes are recorded in the candidate manifest. No DDR drive strengths, UART settings, SPL code, FIT payload or disk offsets change.

A separate board bring-up reports DDR-dependent aborts after training. That is supporting context, not proof for this board: https://github.com/juliovendramini/rk3518_armbian/blob/main/addendum-ddr-and-emmc-install.md . Repeat the crash capture and establish recovery access before testing candidates.
