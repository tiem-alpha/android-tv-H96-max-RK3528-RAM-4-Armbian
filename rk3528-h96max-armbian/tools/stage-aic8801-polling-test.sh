#!/bin/bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin

[[ $(id -u) == 0 ]] || { echo 'Run as root' >&2; exit 1; }
[[ $(uname -r) == 6.1.172-vendor-rk35xx ]] || { echo 'Unexpected kernel' >&2; exit 1; }

base=/home/nguyentiem/h96-wifi-25mhz-20261101
backup=/var/backups/h96-wifi-polling-20261101
module_root=/lib/modules/6.1.172-vendor-rk35xx/kernel/drivers/net/wireless/aicsemi/aic8800
bsp=$module_root/aic8800_bsp/aic8800_bsp.ko
fdrv=$module_root/aic8800_fdrv/aic8800_fdrv.ko
dtb=/boot/dtb/rockchip/rk3528-h96max-stock-rails-net-hdmi-wifi32k.dtb

check() {
    [[ $(sha256sum "$1" | cut -d' ' -f1) == "$2" ]] || {
        echo "SHA-256 mismatch: $1" >&2; exit 1;
    }
}
check "$bsp" de0c2ad395e3e6417363cf1a581a9f519c6420a57dc83fea13081e2a5666bdd5
check "$fdrv" e6dd598ec10e711763eeee3b094036fddc180318da6ac4de436b4df1be637ced
check "$dtb" ca21b5d1031287a0d01e7bb09419397642f1f97fbffd4d7f6f620281a4e688ee
check "$base/aic8800_bsp-polling.ko" 42515356169396cd6a2e1bade927e037db982d68e9257af609427e12a1f781e1
check "$base/aic8800_fdrv-polling.ko" 59e5955bac7e249ef82259130678a3869bf5f99d11cf45de462bd270979cf914
check "$base/sdio-polling-no-nonremovable.dtb" 526ed8531a1d446b97faee2923c665d3a23b1efd67369a35c1d82c58e7903526
for module in "$base/aic8800_bsp-polling.ko" "$base/aic8800_fdrv-polling.ko"; do
    [[ $(modinfo -F vermagic "$module" | cut -d' ' -f1) == $(uname -r) ]] || exit 1
done
if [[ ! -e "$backup" ]]; then
    install -d -m 0755 "$backup"
    install -m 0644 "$bsp" "$backup/aic8800_bsp.ko"
    install -m 0644 "$fdrv" "$backup/aic8800_fdrv.ko"
    install -m 0644 "$dtb" "$backup/baseline.dtb"
fi
check "$backup/aic8800_bsp.ko" de0c2ad395e3e6417363cf1a581a9f519c6420a57dc83fea13081e2a5666bdd5
check "$backup/aic8800_fdrv.ko" e6dd598ec10e711763eeee3b094036fddc180318da6ac4de436b4df1be637ced
check "$backup/baseline.dtb" ca21b5d1031287a0d01e7bb09419397642f1f97fbffd4d7f6f620281a4e688ee

rollback() {
    trap - ERR
    install -m 0644 "$backup/aic8800_bsp.ko" "$bsp"
    install -m 0644 "$backup/aic8800_fdrv.ko" "$fdrv"
    install -m 0644 "$backup/baseline.dtb" "$dtb"
    depmod -a
    sync
    echo 'Stage failed; previous modules and DTB restored.' >&2
}
trap rollback ERR
install -m 0644 "$base/aic8800_bsp-polling.ko" "${bsp}.h96-new"
install -m 0644 "$base/aic8800_fdrv-polling.ko" "${fdrv}.h96-new"
install -m 0644 "$base/sdio-polling-no-nonremovable.dtb" "${dtb}.h96-new"
mv -f "${bsp}.h96-new" "$bsp"
mv -f "${fdrv}.h96-new" "$fdrv"
mv -f "${dtb}.h96-new" "$dtb"
depmod -a
check "$bsp" 42515356169396cd6a2e1bade927e037db982d68e9257af609427e12a1f781e1
check "$fdrv" 59e5955bac7e249ef82259130678a3869bf5f99d11cf45de462bd270979cf914
check "$dtb" 526ed8531a1d446b97faee2923c665d3a23b1efd67369a35c1d82c58e7903526
sync
trap - ERR
echo "Staged polling test; backup: $backup"
echo 'Cold boot required. No boot service or Android partition was changed.'
