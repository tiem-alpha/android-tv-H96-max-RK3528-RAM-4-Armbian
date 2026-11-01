#!/usr/bin/env bash
# Run on the Armbian box as root. Uses an isolated ftrace instance; no driver reload.
set -euo pipefail

[[ $(id -u) -eq 0 ]] || { echo 'Run as root' >&2; exit 1; }
duration=${1:-20}
mode=${3:-active}
[[ $duration =~ ^[0-9]+$ ]] && (( duration >= 5 && duration <= 120 )) || {
    echo 'Duration must be 5..120 seconds' >&2; exit 1;
}
[[ $mode == active || $mode == passive ]] || { echo 'Mode must be active or passive' >&2; exit 1; }

trace_root=/sys/kernel/tracing
instance=$trace_root/instances/aic8801-test-$$
output=${2:-/tmp/aic8801-sdio-$(date +%Y%m%d-%H%M%S)}
mkdir -p "$output"
mkdir "$instance"
reader=''
cleanup() {
    if [[ -n $reader ]]; then kill "$reader" 2>/dev/null || :; wait "$reader" 2>/dev/null || :; fi
    echo 0 > "$instance/tracing_on" 2>/dev/null || :
    echo 0 > "$instance/events/mmc/mmc_request_start/enable" 2>/dev/null || :
    echo 0 > "$instance/events/mmc/mmc_request_done/enable" 2>/dev/null || :
    rmdir "$instance" 2>/dev/null || :
}
trap cleanup EXIT INT TERM

echo 'name == "mmc2" && (cmd_opcode == 52 || cmd_opcode == 53)' > "$instance/events/mmc/mmc_request_start/filter"
echo 'name == "mmc2" && (cmd_opcode == 52 || cmd_opcode == 53)' > "$instance/events/mmc/mmc_request_done/filter"
echo 1 > "$instance/events/mmc/mmc_request_start/enable"
echo 1 > "$instance/events/mmc/mmc_request_done/enable"
echo 1 > "$instance/tracing_on"
cat "$instance/trace_pipe" > "$output/mmc-trace.txt" &
reader=$!

cat /sys/kernel/debug/mmc2/ios > "$output/mmc2-ios.txt" 2>&1 || :
cat /sys/module/aic8800_fdrv/parameters/ps_on > "$output/ps_on.txt" 2>/dev/null || :
cat /sys/module/aic8800_fdrv/parameters/dpsm > "$output/dpsm.txt" 2>/dev/null || :
dmesg > "$output/dmesg-before.txt"

end=$((SECONDS + duration))
while (( SECONDS < end )); do
    if [[ $mode == active ]]; then
        nmcli -w 4 device wifi rescan ifname wlan0 >> "$output/rescan.txt" 2>&1 || :
        sleep 2
    else
        sleep 1
    fi
done

dmesg > "$output/dmesg-after.txt"
nmcli -t device status > "$output/network-status.txt" 2>&1 || :
echo "Saved trace and status in $output"
