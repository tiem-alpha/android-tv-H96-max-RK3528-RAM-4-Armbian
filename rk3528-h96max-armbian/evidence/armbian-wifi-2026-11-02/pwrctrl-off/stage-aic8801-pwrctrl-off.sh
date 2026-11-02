#!/usr/bin/env bash
# Install a matched BSP/FDRV pair for the next boot, or restore the saved pair.
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
(( EUID == 0 )) || { echo 'Run with sudo'; exit 1; }
[[ $(uname -r) == 6.1.172-vendor-rk35xx ]] || { echo 'Unexpected kernel'; exit 1; }
base=$(cd -- "$(dirname -- "$0")" && pwd)
backup=/var/backups/h96-wifi-pwrctrl-off-20261102
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
[[ $(sha256sum "$bsp" | cut -d' ' -f1) == de0c2ad395e3e6417363cf1a581a9f519c6420a57dc83fea13081e2a5666bdd5 ]] || { echo 'BSP changed since preparation'; exit 1; }
[[ $(sha256sum "$fdrv" | cut -d' ' -f1) == e6dd598ec10e711763eeee3b094036fddc180318da6ac4de436b4df1be637ced ]] || { echo 'FDRV changed since preparation'; exit 1; }
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
echo "CONFIG_SDIO_PWRCTRL=n pair installed for next boot. Backup: $backup"
echo "Restore: sudo bash $base/stage-aic8801-pwrctrl-off.sh restore"
echo 'Running modules are unchanged; no reboot or hot reload was performed.'
