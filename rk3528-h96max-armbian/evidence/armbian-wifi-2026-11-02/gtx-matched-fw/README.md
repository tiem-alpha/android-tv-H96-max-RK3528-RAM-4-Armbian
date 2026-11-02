# GTX driver and matching firmware

Source commit a870f7f15170a5899bf0b98769896fd1a7d4bf1e from https://github.com/gtxaspec/aic8800-wifi. Driver: SDIO/driver_fw/driver/aic8800, release 2024_0929_2e313139. Firmware: all 13 files from SDIO/driver_fw/fw/aic8800, including fmacfw_patch.bin required by this driver for AIC8801.

The first GTX boot failed because factory firmware lacked fmacfw_patch.bin. This package pairs the driver with its upstream firmware in /lib/firmware/aic8800-gtx-a870f7f/SDIO/aic8800; Android firmware remains in its original directory. Board patch disables Ubuntu hooks and RX preallocation, and explicitly selects the private firmware path in aic_bsp_driver.h and aicsdio.c. Kernel autoconf.h overrides the Makefile CONFIG_AIC_FW_PATH, so changing only the Makefile is insufficient. Final binary strings were checked to contain the private path and omit the previous path.

Built with matching 6.1.172-vendor-rk35xx headers and GCC 14. Vermagic and imported symbol CRCs checked. SDIO clock 50 MHz and upstream SDIO power control enabled. Final package SHA256SUMS covers both modules and all firmware files.

Installed successfully on 2026-11-02; depmod and sync completed. Final BSP SHA-256 2f103acd4c9f99c41bae1750159055a94641153201df24b374e220f93ec38baf; FDRV 49531c06a94ab52f072e0f0b62b5347f36546b157f6c9f6e0744c11ec9525a5c. All 13 installed firmware hashes match package. Final installed BSP binary firmware path checked. No hot reload or reboot performed; runtime scan remains unverified pending user reboot.

Box package: /home/nguyentiem/h96-gtx-matched-fw-20261102. Immediate prior modules backed up in /var/backups/h96-wifi-gtx-matchedfw-20261102. Restore pre-GTX modules with `sudo bash /home/nguyentiem/h96-gtx-matched-fw-20261102/stage-gtx-matched-fw.sh restore`, then boot again; this uses the checked backup /var/backups/h96-wifi-gtx-20261102. It restores the previous driver that selects the preserved Android firmware. Initial install refuses to overwrite existing backup or firmware directory.
