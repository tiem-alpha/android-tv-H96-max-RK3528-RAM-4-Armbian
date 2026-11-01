#!/usr/bin/env bash
# One-shot, manually run diagnostic for H96 Max RK3528. Ethernet stays up.
set -euo pipefail

[[ $(id -u) -eq 0 ]] || { echo 'Run as root' >&2; exit 1; }
[[ $(uname -r) == 6.1.172-vendor-rk35xx ]] || { echo 'Unexpected kernel' >&2; exit 1; }
[[ $(readlink -f /sys/bus/platform/devices/ffc10000.mmc/driver) == /sys/bus/platform/drivers/dwmmc_rockchip ]] || {
    echo 'SDIO host is not bound to dwmmc_rockchip' >&2; exit 1;
}
nmcli -t -f DEVICE,STATE device status | grep -q '^end0:connected$' || {
    echo 'Ethernet end0 must be connected' >&2; exit 1;
}
grep -q 'gpio-132 .*reset.*out hi ACTIVE LOW' /sys/kernel/debug/gpio || {
    echo 'GPIO4_PA4 is not in the expected released-reset state' >&2; exit 1;
}

out=${1:-/tmp/aic8801-gpio4-$(date +%Y%m%d-%H%M%S)}
[[ ! -e $out ]] || { echo "Output already exists: $out" >&2; exit 1; }
mkdir -m 0755 "$out"
trace=/sys/kernel/tracing/instances/aic8801-gpio4-$$
mkdir "$trace"
reader=''
unbound=0
cleanup() {
    if (( unbound )); then
        echo ffc10000.mmc > /sys/bus/platform/drivers/dwmmc_rockchip/bind 2>> "$out/restore-error.txt" || :
    fi
    if [[ -n $reader ]]; then kill "$reader" 2>/dev/null || :; wait "$reader" 2>/dev/null || :; fi
    echo 0 > "$trace/tracing_on" 2>/dev/null || :
    echo 0 > "$trace/events/gpio/gpio_value/enable" 2>/dev/null || :
    echo 0 > "$trace/events/mmc/mmc_request_start/enable" 2>/dev/null || :
    echo 0 > "$trace/events/mmc/mmc_request_done/enable" 2>/dev/null || :
    rmdir "$trace" 2>/dev/null || :
}
trap cleanup EXIT INT TERM

echo 'gpio == 132' > "$trace/events/gpio/gpio_value/filter"
echo 'name == "mmc2" && (cmd_opcode == 52 || cmd_opcode == 53)' > "$trace/events/mmc/mmc_request_start/filter"
echo 'name == "mmc2" && (cmd_opcode == 52 || cmd_opcode == 53)' > "$trace/events/mmc/mmc_request_done/filter"
echo 1 > "$trace/events/gpio/gpio_value/enable"
echo 1 > "$trace/events/mmc/mmc_request_start/enable"
echo 1 > "$trace/events/mmc/mmc_request_done/enable"
echo 1 > "$trace/tracing_on"
cat "$trace/trace_pipe" > "$out/trace.txt" & reader=$!

date -Is > "$out/started-at.txt"
cat /sys/kernel/debug/gpio > "$out/gpio-before.txt"
cat /sys/kernel/debug/mmc2/ios > "$out/mmc-before.txt"
dmesg > "$out/dmesg-before.txt"

echo ffc10000.mmc > /sys/bus/platform/drivers/dwmmc_rockchip/unbind
unbound=1
sleep 2
cat /sys/kernel/debug/gpio > "$out/gpio-during.txt"
echo ffc10000.mmc > /sys/bus/platform/drivers/dwmmc_rockchip/bind
unbound=0
sleep 10
nmcli -w 5 device wifi rescan ifname wlan0 > "$out/rescan.txt" 2>&1 || :
sleep 10
nmcli -f IN-USE,SSID,CHAN,SIGNAL device wifi list ifname wlan0 > "$out/networks.txt" 2>&1 || :

cat /sys/kernel/debug/gpio > "$out/gpio-after.txt"
cat /sys/kernel/debug/mmc2/ios > "$out/mmc-after.txt" 2>&1 || :
dmesg > "$out/dmesg-after.txt"
nmcli -t device status > "$out/network-after.txt"
find /sys/bus/sdio/devices -maxdepth 2 -name uevent -print -exec cat {} \; > "$out/sdio-after.txt" 2>&1 || :
date -Is > "$out/finished-at.txt"
echo "Saved GPIO4 reset and SDIO trace in $out"
