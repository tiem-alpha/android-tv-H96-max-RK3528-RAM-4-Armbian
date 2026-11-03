# Bundled AIC8800 source for H96 Max RK3528

Source and firmware were copied from the downloaded GTX checkout at commit `a870f7f15170a5899bf0b98769896fd1a7d4bf1e` of https://github.com/gtxaspec/aic8800-wifi.

- `driver/`: `SDIO/driver_fw/driver/aic8800`, with both patches in `patches/patch/misc/aic8800-gtx/` already applied directly.
- `firmware/`: all 13 files from `SDIO/driver_fw/fw/aic8800`, verified against the project's SHA-256 manifest.
- Fixes cover the kernel 6.1 port, NULL checks before bus/SDIO/global-state access, error propagation when BSP/init fails, thread/allocation checks, and cleanup on reviewed error paths. RX preallocation and SDIO power control remain enabled.

Builds use this local source without cloning/fetching the driver or applying these patches again. Edit `driver/` here. The launcher stages it under `armbian-build/userpatches/h96-vendor/aic8800/driver` so the Docker build can access it. The kernel hook hashes all staged source files into the cache key. The two original patches remain as a record of the changes. Preserve upstream authorship and licensing notices.

The upstream commit records provenance; it is not a network dependency for Wi-Fi builds. This source corresponds to the fixes tested on the box. A complete newly built image still requires hardware validation. The GPIO38 LED-restore workaround remains necessary.
