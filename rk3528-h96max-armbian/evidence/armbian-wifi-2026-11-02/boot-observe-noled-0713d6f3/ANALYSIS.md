# Wi-Fi success with LED restore masked

Boot ID 0713d6f3-86b8-4498-95de-4f50e01a3209. Same GTX RX-preallocation-enabled BSP/FDRV, same matched firmware, same passive trace configuration as failing boot 267bea0d. Sole intentional operational change: armbian-led-state.service masked (without stopping/reloading drivers).

Results: wlan0 auto-connected to existing NguyenTiem profile, IPv4 192.168.1.9/24, gateway 192.168.1.1. Forced scan returned many APs on 2.4 and 5 GHz. Ping explicitly bound to wlan0: gateway 192.168.1.1 3/3 replies, Internet 1.1.1.1 3/3 replies, zero loss in these short checks. Initial ping to 192.168.0.1 got no replies; that was the Ethernet-side router, not wlan0's DHCP gateway, so it is not evidence of failed Wi-Fi.

Trace: GPIO38 only has initial set-high event at 4.441483; no later low pulse. No MMC2 command error after trace time 25s; kernel log has no wakeup failure, command timeout, command-queue crash or Oops. All trace per-CPU overrun and dropped-event counters zero. In failing baseline, LED restore produced GPIO38 low pulse ~4.236ms about 1.122s before runtime wake timeout.

This is strong controlled-boot evidence implicating LED restore's GPIO38 pulse. It is not a physical measurement proving GPIO38 is a module supply or reset pin, and is not a long-duration reliability test. Keep armbian-led-state.service masked while validating further. Kernel DT declares this pin as gpio-leds pwr-wifi; hardware role should be checked before permitting it to toggle again.

Observation services completed successfully, restored original boot options and disabled themselves. GPIO38 brightness remains 1. Logs copied from /run/h96-wifi-boot-trace to this folder. No intentional changes to Bluetooth, firmware, DTB or driver between the paired trials.
