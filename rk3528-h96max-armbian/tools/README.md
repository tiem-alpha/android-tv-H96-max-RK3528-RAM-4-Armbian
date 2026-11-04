# Maintained tools

Run these tools from the `rk3528-h96max-armbian` directory.

| Tool | Purpose | Used by the image build |
| --- | --- | --- |
| `prepare-aic8800-gtx.sh` | Verify all 13 bundled GTX firmware files and stage the overlay | Yes, before compilation |
| `prepare-local-build.py` | Validate the local Armbian snapshot, apply local compatibility adapters, and record an input SHA-256 | Yes, after staging inputs |
| `install-emmc.py` | Read-only preflight remains available; installation and resume are blocked after the SPL incident | No |
| `prepare-ddr-diagnostic.py` | Reproduce the incident loader and prepare an isolated DDR3 528 MHz diagnostic artifact; never flash | No |
| `audit-bootloader.py` | Check retained SPL/U-Boot ELF driver pointers, DTBs and FIT payload hashes without accessing devices | No |
| `check-rk3528-mmu.py` | Run the retained page-table construction C code on the host and check mapping/allocation arithmetic | No |
| `replay-spl-early.py` | Replay the pinned incident SPL in a controlled CPU emulator with memory-write hooks; requires Unicorn/Capstone and models hardware effects | No |
| `check-early-calloc.py` | Compile the actual vendor calloc body on the host and check allocation failure, size overflow and normal clearing | No |
| `capture-uart.py` | Capture serial console output for boot diagnosis; requires pyserial | No; maintained diagnostic utility |

To prepare inputs without compiling or launching Docker:

```sh
H96_PREPARE_ONLY=yes ./build-desktop.sh
```

Dated Wi-Fi staging, rollback, tracing and network-reset scripts are retained under [experiments/wifi-2026-11-02](../experiments/wifi-2026-11-02/README.md). The old Android firmware extractor is under [experiments/android-firmware](../experiments/android-firmware/README.md). They are not part of the current build. Experimental scripts already removed before this cleanup have not been restored.
