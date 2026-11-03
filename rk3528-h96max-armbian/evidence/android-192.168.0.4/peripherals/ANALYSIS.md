# Android peripherals: FD655, LEDs, composite AV and HDMI

Historical extraction retained the live DTB/decoded DTS, `kernel.config`, `FD655_Demo` and `init.rk3528.rc` locally.

| Peripheral | Android evidence | Armbian status at extraction time |
| --- | --- | --- |
| Seven-segment display | `CONFIG_LEDS_FD655=y`, `fd655_dev`, `/dev/fd655_dev`; GPIO4 lines 19/20 | Kernel 6.1 lacked the Android FD655 source; a port or suitable controller was needed |
| Time/network display | `FD655_Demo` starts after `sys.boot_completed`; uses time/localtime, wlan0/eth0 and ioctl | Needed a Linux program using actual interface names and an appropriate FD655 interface |
| Power/Wi-Fi LED | gpio-leds pwr-wifi on GPIO1 line 6, default-on, trigger none | Defined in Armbian DTS; sysfs control was available, but later GPIO38 results show it must not be toggled casually |
| Composite AV | `CONFIG_ROCKCHIP_DRM_TVE=y`, `card0-TV-1` | Driver/route existed; physical output still needed testing |
| HDMI | `CONFIG_ROCKCHIP_DW_HDMI=y`, `card0-HDMI-A-1` | Driver/route existed; Linux validation was still required |

FD655, TVE and HDMI were built into Android's kernel, with no separate modules to copy. `FD655_Demo` is an Android executable, not directly runnable on Debian. The separate `pwr-wifi` GPIO LED does not itself implement the front panel's network indicators; the display program chooses those icons.

[`linux_openvfd`](https://github.com/arthur-liberman/linux_openvfd) was downloaded into `evidence/linux_openvfd` at commit `775bdf8c0f6e959a6e9de043ee6838fe947994c6`. It lists FD655/FD6551 but had not yet been configured/validated for this box at extraction time. It is not the original Android driver source. The later Python FD655 service is described in the current LED README.

Android logs showed HDMI 1920×1080p60. TVE enabled 720×576i50 and later disabled it. Physical composite AV output was not visually verified.
