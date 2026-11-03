#!/usr/bin/env bash
# Clear saved Wi-Fi state and test a fresh scan without rebooting the box.
set -euo pipefail

(( EUID == 0 )) || { echo 'Run with sudo on the box' >&2; exit 1; }
command -v nmcli >/dev/null
nmcli -t -f DEVICE,STATE device status | grep -q '^end0:connected$' || {
    echo 'Ethernet end0 must be connected' >&2; exit 1;
}

out="/var/log/h96-wifi-clean-$(date +%Y%m%d-%H%M%S)"
mkdir -m 0700 "$out"
nmcli -t -f NAME,UUID,TYPE,DEVICE connection show > "$out/connections-before.txt"
journalctl -b -k --no-pager > "$out/kernel-before.txt"
cp -a /etc/NetworkManager/system-connections "$out/system-connections-backup"
if [[ -e /var/lib/NetworkManager/seen-bssids ]]; then
    cp -a /var/lib/NetworkManager/seen-bssids "$out/seen-bssids-backup"
fi

mapfile -t wifi_ids < <(nmcli -t -f UUID,TYPE connection show | awk -F: '$2 == "802-11-wireless" {print $1}')
for id in "${wifi_ids[@]}"; do
    nmcli connection delete uuid "$id"
done
rm -f /var/lib/NetworkManager/seen-bssids
nmcli radio wifi off
sleep 3
nmcli radio wifi on
sleep 3

nmcli -w 25 -f IN-USE,SSID,CHAN,SIGNAL,SECURITY device wifi list ifname wlan0 --rescan yes \
    > "$out/scan.txt" 2> "$out/scan-error.txt" || true
nmcli -t -f NAME,UUID,TYPE,DEVICE connection show > "$out/connections-after.txt"
nmcli -t device status > "$out/devices-after.txt"
journalctl -b -k --no-pager > "$out/kernel-after.txt"

echo "Log and profile backup: $out"
cat "$out/scan.txt"
if [[ -s "$out/scan-error.txt" ]]; then cat "$out/scan-error.txt" >&2; fi
echo 'Hardware power cycle: unavailable through the current device tree (no dedicated Wi-Fi power rail control).'
echo 'GPIO4_PA4 is reset, not power; hot SDIO rebind previously caused a kernel Oops.'
