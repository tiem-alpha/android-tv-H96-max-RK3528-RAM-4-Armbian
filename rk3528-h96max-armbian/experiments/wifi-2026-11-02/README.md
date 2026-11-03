# Archived Wi-Fi experiments (2026-11-02)

These scripts supported the dated AIC8801 investigation. They are not invoked by `build-desktop.sh`, are not installed into the production image, and are retained together for reproducibility. The trace installer resolves its companion files relative to this directory.

The staging/restore scripts refer to the development box, kernel 6.1.172, dated backups and module/firmware packages that are not included here. They are historical procedures, not general installers. Running them can change modules, boot options or saved network profiles. Read the script and the associated investigation before using it.

- `install-h96-wifi-boot-observe.py`, `h96-wifi-*`: one-run passive boot tracing.
- `stage-h96-no-led-restore-test.py`: repeats the paired boot trial with LED restore masked.
- `stage-gtx-matched-fw.sh`, `restore-gtx-nullguard.sh`: dated module deployment/rollback helpers.
- `reset-wifi-state-and-scan.sh`: destructive saved-network-state experiment; not part of the Wi-Fi fix.

See [GPIO38 findings](../../docs/WIFI_GPIO38_LED_RESTORE_FIX_2026-11-02.md) and [boot observation](../../docs/WIFI_BT_BOOT_OBSERVE_2026-11-02.md). The production pipeline applies the GPIO38 workaround directly and uses bundled source and firmware.
