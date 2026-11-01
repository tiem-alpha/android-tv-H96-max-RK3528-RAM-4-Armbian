#!/bin/bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
[[ $(id -u) == 0 ]] || { echo 'Run as root' >&2; exit 1; }
backup=/var/backups/h96-wifi-polling-20261101
module_root=/lib/modules/6.1.172-vendor-rk35xx/kernel/drivers/net/wireless/aicsemi/aic8800
bsp=$module_root/aic8800_bsp/aic8800_bsp.ko
fdrv=$module_root/aic8800_fdrv/aic8800_fdrv.ko
dtb=/boot/dtb/rockchip/rk3528-h96max-stock-rails-net-hdmi-wifi32k.dtb
check() {
    [[ $(sha256sum "$1" | cut -d' ' -f1) == "$2" ]] || { echo "SHA-256 mismatch: $1" >&2; exit 1; }
}
check "$backup/aic8800_bsp.ko" de0c2ad395e3e6417363cf1a581a9f519c6420a57dc83fea13081e2a5666bdd5
check "$backup/aic8800_fdrv.ko" e6dd598ec10e711763eeee3b094036fddc180318da6ac4de436b4df1be637ced
check "$backup/baseline.dtb" ca21b5d1031287a0d01e7bb09419397642f1f97fbffd4d7f6f620281a4e688ee
install -m 0644 "$backup/aic8800_bsp.ko" "$bsp"
install -m 0644 "$backup/aic8800_fdrv.ko" "$fdrv"
install -m 0644 "$backup/baseline.dtb" "$dtb"
depmod -a
check "$bsp" de0c2ad395e3e6417363cf1a581a9f519c6420a57dc83fea13081e2a5666bdd5
check "$fdrv" e6dd598ec10e711763eeee3b094036fddc180318da6ac4de436b4df1be637ced
check "$dtb" ca21b5d1031287a0d01e7bb09419397642f1f97fbffd4d7f6f620281a4e688ee
sync
echo 'Restored pre-test modules and DTB. Cold boot to load them.'
