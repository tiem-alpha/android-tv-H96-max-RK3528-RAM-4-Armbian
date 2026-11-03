# Wi-Fi modules extracted from Android on box 192.168.0.4

ADB TCP connected successfully on 2026-11-01. The box ran Android kernel `5.10.157`, SDIO `5449:0145`/`544a:0146`, with `aic8800_bsp` and `aic8800_fdrv` loaded. Three original modules were copied from `/vendor_dlkm/lib/modules/` into the local `modules/` evidence directory. Two raw diagnostic text files were deleted at the user's request.

| Module | SHA-256 | Notes |
| --- | --- | --- |
| `aic8800_bsp.ko` | `d08c6bb8e19d90ce42e7df68b3376655540e57dcd5d2e554facb4ca4e02728ec` | `RELEASE_DATE:2023_0207_1037` |
| `aic8800_fdrv.ko` | `1d3bea6dfbef8504faf4f19c4679d1c6b8954f30c8fb144b6110f2a8ea3ec75e` | AIC8801 alias; version `6.4.3.0` |
| `aic8800_btlpm.ko` | `40852ecf26bcb75631be2be80f1aecfe656985e2984289810fac6afa9210f7f5` | Bluetooth low power |

Android loaded `fw_patch_table_u03.bin`, `fw_adid_u03.bin`, `fw_patch_u03.bin` and `fmacfw.bin` from `/vendor/etc/firmware/`. Captured logs showed completed firmware initialization and repeated scan confirmations (`rwnx_rx_scanu_start_cfm()`), without `sdio wakeup fail`.

The Android BSP symbol/string tables lacked `aicwf_sdio_wakeup`, `aicwf_sdio_sleep_allow` and the wake-failure message, while the earlier Armbian source contained them under upstream-default `CONFIG_SDIO_PWRCTRL=y`. This supported investigating BSP sleep control, without proving a sole cause. A worktree's `CONFIG_SDIO_PWRCTRL := n` was left from an earlier trial, not the original running configuration; that trial failed to return on the network. Android FDRV has its own sleep/wake path, as later analysis clarified.

These modules have `vermagic 5.10.157` and cannot be loaded directly into Armbian 6.1.172. They are comparison evidence for a rebuilt Linux port. No original driver source was found on the examined Android partitions.
