# Wi-Fi and Bluetooth image integration

Updated 2026-11-03. This document describes the current pipeline. Earlier fetch-at-build and clean-Git-checkout requirements have been replaced by bundled Wi-Fi source/firmware and local Armbian snapshot support.

## Build components

- `patches/config/h96-aic8800.conf` records the GTX origin, upstream commit, original subdirectories and installation path.
- `patches/config/h96-aic8800-firmware.sha256` contains hashes for all 13 matching firmware files.
- `patches/vendor/aic8800/driver` contains the downloaded source with kernel 6.1, NULL/init guards and RX preallocation fixes already applied. No Wi-Fi Git fetch or patch application occurs during the build.
- `tools/prepare-aic8800-gtx.sh` verifies bundled firmware, copies it into the image overlay and checks the staged copy. `build-desktop.sh` calls it automatically. `H96_AIC_SOURCE_DIR` is no longer used.
- The launcher stages the driver under `userpatches/h96-vendor/aic8800/driver`, a directory Armbian mounts into Docker. The extension hashes that source, configuration and firmware manifest into the kernel cache key, integrates Kconfig/Makefile paths, and selects BSP/FDRV support as modules.
- SDIO power control and RX preallocation are enabled. The driver selects 50 MHz; the H96 DTS also explicitly caps SDIO at 50 MHz. The SD-card controller is separately capped at 25 MHz.
- `customize-image.sh` installs/verifies the GTX firmware, masks the GPIO38 LED-restore service and installs/enables the FD655 clock as before.
- The post-image hook verifies firmware again, establishes BSP-before-FDRV autoload order, masks LED restore, configures UART2 Bluetooth at 1.5 Mbaud, runs `rfkill unblock bluetooth` before attach, enables BlueZ and sets `AutoEnable=true`.
- `/etc/h96-radio-build.conf` records radio provenance/settings. Experimental trace services are not installed or enabled.

The build does not require extracting Android firmware. Factory firmware remains comparison/recovery evidence; it is not mixed with the complete GTX set.

## Local build tree

Use the complete existing `armbian-build` source tree. Its framework `.git` directory is not required. `tools/prepare-local-build.py` validates the layout, adapts framework logging and records a SHA-256 of build inputs. Git discovery is bounded so nested source caches cannot mistake the enclosing project for the framework repository. Kernel/U-Boot source management still uses Armbian's internal Git machinery; this is not a guarantee of a fully offline or Git-free build.

The H96 extension pins kernel commit `4ee92c1e3bd78ddc6f57c5a9dc056281ea863072` (6.1.172). Six empty userpatch overrides disable changes already present in that commit; each was verified by a complete reverse dry-run. Reassess them before changing the kernel baseline.

```sh
H96_PREPARE_ONLY=yes ./build-desktop.sh
H96_DOCKER_LOCAL_BASE=yes H96_BUILD_THREADS=8 ./build-desktop.sh
```

`H96_DOCKER_LOCAL_BASE=yes` avoids an age-triggered Docker base refresh when the base image is present. Other source/package downloads may still occur. Missing firmware or a checksum mismatch stops preparation; do not change expected hashes to bypass a failure.

## Validation performed

1. Verified all 13 firmware hashes and shell syntax.
2. Ran the kernel integration hook twice in isolated staging: no duplicate Kconfig/Makefile entries; source matches the bundled driver except for intentional Kconfig path changes.
3. Earlier component checks compared generated C/header/Makefile files with the boot-tested RX-preallocation build, exercised a minimal Kconfig tree, and built BSP/FDRV using matching 6.1.172 headers and GCC 14. Vermagic and every imported symbol CRC matched.
4. Earlier customization checks used an isolated minimal chroot. The latest post-image check ran twice against a temporary rootfs using `systemctl --root`, without starting services. A minimal placeholder BlueZ unit checked enable-link creation; it did not prove installation of the real BlueZ package. Firmware, GPIO38 mask, autoload, Bluetooth unblock/attach and one `AutoEnable=true` entry passed.
5. Earlier negative checks rejected corrupted firmware. The current snapshot adapter rejects incomplete framework trees; local preparation also passed with Git invocation blocked and produced a stable input hash on repeated runs.
6. Checked the actual compiling kernel tree: bundled driver contents and Wi-Fi/GPIO/Bluetooth kernel configuration match the intended inputs. Complete image validation remains separate.

## Checks after flashing the new image

```sh
cat /etc/h96-radio-build.conf
systemctl is-enabled armbian-led-state.service  # masked
nmcli device wifi list
ip -4 addr show wlan0
bluetoothctl show
systemctl status h96max-bluetooth.service --no-pager
systemctl status h96-fd655.service --no-pager
```

Test Wi-Fi over cold boot/reboot, DHCP and traffic explicitly bound to `wlan0`, Bluetooth power-on/discovery, and FD655 date/time/icons. Pairing, A2DP, suspend and long-duration reliability remain unverified. Keep Ethernet and SD recovery available. eMMC remains disabled; follow the separate installation plan before attempting migration.
