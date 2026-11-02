# GTX SDIO driver for H96 Max RK3528

Source: https://github.com/gtxaspec/aic8800-wifi commit a870f7f15170a5899bf0b98769896fd1a7d4bf1e, SDIO/driver_fw/driver/aic8800 (generic SDIO source, release 2024_0929_2e313139). This is not the exact Android February 2023 driver. Board integration patch in board-build.patch disables Ubuntu platform hooks, disables RX skb preallocation to match the existing board integration, and selects the existing factory firmware path /lib/firmware/aic8800/SDIO/aic8800D80. Upstream SDIO power control remains enabled, upstream SDIO clock 50 MHz. Existing DTB is retained.

Build succeeded using GCC 14 and matching 6.1.172-vendor-rk35xx headers. Vermagic matches and every imported symbol CRC was checked against kernel and candidate Module.symvers. Runtime behavior remains unverified until next boot. Full build workspace/log: /home/nguyentiem/h96-gtx-generic-port.

Deployment package: /home/nguyentiem/h96-gtx-20261102 on box. Installer backs up current BSP/FDRV to /var/backups/h96-wifi-gtx-20261102. Restore with sudo bash /home/nguyentiem/h96-gtx-20261102/stage-gtx.sh restore; requires another boot. No hot reload or automatic reboot.
