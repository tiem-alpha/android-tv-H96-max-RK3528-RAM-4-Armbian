#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
(( EUID == 0 )) || { echo 'Run with sudo'; exit 1; }
[[ $(uname -r) == 6.1.172-vendor-rk35xx ]] || { echo 'Unexpected kernel'; exit 1; }
base=$(cd -- "$(dirname -- "$0")" && pwd)
backup=/var/backups/h96-wifi-gtx-matchedfw-20261102
firmware=/lib/firmware/aic8800-gtx-a870f7f/SDIO/aic8800
bsp=$(modinfo -n aic8800_bsp)
fdrv=$(modinfo -n aic8800_fdrv)
if [[ ${1:-install} == restore ]]; then
    previous=/var/backups/h96-wifi-gtx-20261102
    (cd "$previous" && sha256sum -c SHA256SUMS)
    install -m 0644 "$previous/aic8800_bsp.ko" "$bsp"
    install -m 0644 "$previous/aic8800_fdrv.ko" "$fdrv"
    depmod -a
    sync
    echo 'Pre-GTX modules restored on disk. Reboot required.'
    exit 0
fi
[[ ${1:-install} == install ]] || exit 1
nmcli -t -f DEVICE,STATE device status | grep -q '^end0:connected$'
(cd "$base" && sha256sum -c SHA256SUMS)
for module in aic8800_bsp aic8800_fdrv; do
    [[ $(modinfo -F vermagic "$base/$module.ko") == $(modinfo -F vermagic "$module") ]]
done
[[ ! -e $backup && ! -e $firmware ]] || { echo 'Backup or firmware directory already exists; inspect before repeating'; exit 1; }
install -d -m 0700 "$backup"
cp -a "$bsp" "$backup/aic8800_bsp.ko"
cp -a "$fdrv" "$backup/aic8800_fdrv.ko"
(cd "$backup" && sha256sum aic8800_bsp.ko aic8800_fdrv.ko > SHA256SUMS)
journalctl -b -k --no-pager > "$backup/kernel-before.txt"
trap 'install -m 0644 "$backup/aic8800_bsp.ko" "$bsp"; install -m 0644 "$backup/aic8800_fdrv.ko" "$fdrv"; depmod -a' ERR
install -d -m 0755 "$firmware"
for file in "$base"/firmware/*; do install -m 0644 "$file" "$firmware/"; done
install -m 0644 "$base/aic8800_bsp.ko" "$bsp"
install -m 0644 "$base/aic8800_fdrv.ko" "$fdrv"
depmod -a
sync
trap - ERR
sha256sum "$bsp" "$fdrv"
echo "GTX modules and matched firmware installed. Backup: $backup"
echo "Firmware: $firmware"
echo 'Reboot required; no hot reload or reboot performed.'
