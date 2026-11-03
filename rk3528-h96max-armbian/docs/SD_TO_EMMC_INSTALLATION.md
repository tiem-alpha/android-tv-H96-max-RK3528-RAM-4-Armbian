# Installing Armbian from SD onto eMMC — H96 Max RK3528

Updated 2026-11-03. The user plans to migrate to eMMC one step at a time. This is a preparation plan, not a validated eMMC installation procedure. No installation step below has been confirmed complete.

## Starting state

- Armbian boots from SD. The baseline DTB disables `sdhci` (eMMC, `mmc@ffbf0000`).
- `emmc-enabled-from-baseline.dtb` was previously prepared, but installation was postponed and the SD DTB restored to baseline. eMMC has not been written. See the [recovery guide](RECOVERY.md).
- Patched GTX Wi-Fi and the FD655 date/time display have worked on the box. Wi-Fi source and all matching firmware are bundled in `patches/vendor/aic8800`; NULL/init fixes are applied directly. The build does not fetch the Wi-Fi driver from Git. Both features are integrated into the pipeline, but a complete rebuilt image still needs hardware validation.
- eMMC bootloader compatibility and installation have not been established for this box. Do not assume an SD image can be copied unchanged to eMMC or that `armbian-install` supports this configuration.

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
| 1. Record SD system | Not performed under this plan | — |
| 2. Detect eMMC | Not performed | — |
| 3. Backup/recovery | Not performed | — |
| 4. Select boot/install method | Not performed | — |
| 5. Write eMMC | Not performed | — |
| 6. Boot without SD | Not performed | — |
