# Maintained tools

Run these tools from the `rk3528-h96max-armbian` directory.

| Tool | Purpose | Used by the image build |
| --- | --- | --- |
| `prepare-aic8800-gtx.sh` | Verify all 13 bundled GTX firmware files and stage the overlay | Yes, before compilation |
| `prepare-local-build.py` | Validate the local Armbian snapshot, apply local compatibility adapters, and record an input SHA-256 | Yes, after staging inputs |
| `capture-uart.py` | Capture serial console output for boot diagnosis; requires pyserial | No; maintained diagnostic utility |

To prepare inputs without compiling or launching Docker:

```sh
H96_PREPARE_ONLY=yes ./build-desktop.sh
```

Dated Wi-Fi staging, rollback, tracing and network-reset scripts are retained under [experiments/wifi-2026-11-02](../experiments/wifi-2026-11-02/README.md). The old Android firmware extractor is under [experiments/android-firmware](../experiments/android-firmware/README.md). They are not part of the current build. Experimental scripts already removed before this cleanup have not been restored.
