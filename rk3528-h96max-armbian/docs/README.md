# Documentation

Use the [main README](../README.md) for building and writing the SD image. These English documents describe the supported configuration, validation boundaries and planned next steps.

- [Radio integration](BUILD_RADIO_INTEGRATION_2026-11-02.md): bundled Wi-Fi source/firmware, local framework build and Bluetooth configuration.
- [GPIO38 workaround](WIFI_GPIO38_LED_RESTORE_FIX_2026-11-02.md): paired-boot evidence for Wi-Fi recovery and Bluetooth checks.
- [Recovery and incident analysis](RECOVERY.md): the October 31 SDMMC fix and November 3 stale-superblock failure, including symptoms, evidence, confirmed cause, repair steps, changed files/metadata and verification limits.
- [Prebuild review](PREBUILD_CHECK_2026-11-03.md): checks behind the current build, Docker staging and kernel compatibility fixes.
- [SD-to-eMMC plan](SD_TO_EMMC_INSTALLATION.md): installation is not yet validated; eMMC remains disabled.
- [FD655 display](../led/README.md): date/time, icons and GPIO mapping.
- [Maintained tools](../tools/README.md): build preparation and UART capture.
- [Passive boot observation](WIFI_BT_BOOT_OBSERVE_2026-11-02.md): diagnostic design and limitations behind the GPIO38 finding.

The two paired-boot reports/raw traces and driver-fix reports under `evidence/` remain useful for reproducing the current fix. Superseded bring-up diaries, failed-trial reports and stopped-build logs have been removed. Some historical binary artifacts are local-only; inline paths do not imply they are committed.

Archived diagnostic tools remain under [experiments/wifi-2026-11-02](../experiments/wifi-2026-11-02/README.md); the old Android firmware extractor is under [experiments/android-firmware](../experiments/android-firmware/README.md). Neither is used by production builds. Third-party source/licensing documentation is retained.
