#!/usr/bin/env bash
# Host-side, read-only snapshot. No sudo, driver reload, GPIO, scan, or reboot.
set -euo pipefail

host=${1:-nguyentiem@192.168.0.3}
out=${2:-evidence/aic8801-readonly-$(date +%Y%m%d-%H%M%S)}
[[ ! -e $out ]] || { echo "Output already exists: $out" >&2; exit 1; }
mkdir -p "$out"
read_remote() { timeout 15s ssh -o BatchMode=yes -o ConnectTimeout=5 "$host" "$1"; }

read_remote 'uname -a; uptime -s; cat /proc/cmdline' > "$out/system.txt"
read_remote 'dmesg' > "$out/dmesg.txt"
read_remote 'lsmod' > "$out/modules.txt"
read_remote 'nmcli -t device status; ip -brief address' > "$out/network.txt"
read_remote 'for f in /sys/bus/sdio/devices/*/uevent; do if test -f "$f"; then printf "%s\n" "$f"; cat "$f"; fi; done' > "$out/sdio-devices.txt"
read_remote 'cat /boot/armbianEnv.txt; findmnt /boot -no SOURCE,TARGET' > "$out/boot.txt"
read_remote 'for f in /sys/module/aic8800_fdrv/parameters/ps_on /sys/module/aic8800_fdrv/parameters/dpsm /sys/class/mmc_host/mmc2/device/power/control; do if test -r "$f"; then printf "%s=" "$f"; cat "$f"; fi; done' > "$out/power-settings.txt"

echo "Read-only snapshot saved to $out"
