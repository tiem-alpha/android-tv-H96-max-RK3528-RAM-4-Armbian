#!/usr/bin/env bash
# Install a matched BSP/FDRV pair for the next boot, or restore the saved pair.
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
(( EUID == 0 )) || { echo 'Run with sudo'; exit 1; }
[[ $(uname -r) == 6.1.172-vendor-rk35xx ]] || { echo 'Unexpected kernel'; exit 1; }
base=$(cd -- "$(dirname -- "$0")" && pwd)
backup=/var/backups/h96-wifi-rxprealloc-20261102
bsp=$(modinfo -n aic8800_bsp)
fdrv=$(modinfo -n aic8800_fdrv)

if [[ ${1:-install} == restore ]]; then
    (cd "$backup" && sha256sum -c SHA256SUMS)
    install -m 0644 "$backup/aic8800_bsp.ko" "$bsp"
    install -m 0644 "$backup/aic8800_fdrv.ko" "$fdrv"
    depmod -a
    sync
    echo 'Previous modules restored on disk. A new boot is required.'
    exit 0
fi
[[ ${1:-install} == install ]] || { echo 'Usage: script [install|restore]'; exit 1; }
[[ ! -e $backup ]] || { echo "Backup already exists: $backup; refusing to overwrite"; exit 1; }
nmcli -t -f DEVICE,STATE device status | grep -q '^end0:connected$' || {
    echo 'Connected Ethernet end0 is required'; exit 1;
}
[[ $(sha256sum "$bsp" | cut -d' ' -f1) == 73f486ea36cd77e7d0734e306eb4aec08bfbde8fefb31db26e1be1a45b2cfaec ]] || { echo 'BSP changed since preparation'; exit 1; }
[[ $(sha256sum "$fdrv" | cut -d' ' -f1) == 451d2a70af1cace115c39bca848b16f09ba1eb22db7abd7c62d592234e6ed4dc ]] || { echo 'FDRV changed since preparation'; exit 1; }
(cd "$base" && sha256sum -c SHA256SUMS)
for module in aic8800_bsp aic8800_fdrv; do
    [[ $(modinfo -F vermagic "$base/$module.ko") == $(modinfo -F vermagic "$module") ]] || { echo "Vermagic mismatch: $module"; exit 1; }
done
install -d -m 0700 "$backup"
cp -a "$bsp" "$backup/aic8800_bsp.ko"
cp -a "$fdrv" "$backup/aic8800_fdrv.ko"
(cd "$backup" && sha256sum aic8800_bsp.ko aic8800_fdrv.ko > SHA256SUMS)
journalctl -b -k --no-pager > "$backup/kernel-before.txt"
trap 'install -m 0644 "$backup/aic8800_bsp.ko" "$bsp"; install -m 0644 "$backup/aic8800_fdrv.ko" "$fdrv"; depmod -a' ERR
install -m 0644 "$base/aic8800_bsp.ko" "$bsp"
install -m 0644 "$base/aic8800_fdrv.ko" "$fdrv"
depmod -a
sync
trap - ERR
echo "GTX CONFIG_PREALLOC_RX_SKB=y pair installed for next boot. Backup: $backup"
echo "Restore: sudo bash $base/stage-rxprealloc.sh restore"
echo 'Running modules are unchanged; no reboot or hot reload was performed.'
