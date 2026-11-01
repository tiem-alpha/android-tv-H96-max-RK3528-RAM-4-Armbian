#!/bin/bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin

[[ $(id -u) == 0 ]] || { echo 'Run as root' >&2; exit 1; }
[[ $(uname -r) == 6.1.172-vendor-rk35xx ]] || { echo 'Unexpected kernel' >&2; exit 1; }

mode=${1:-}
case "$mode" in
    original)
        source_dir=/var/backups/h96-wifi-flowctrl-20261101
        source_bsp=$source_dir/aic8800_bsp-original.ko
        source_fdrv=$source_dir/aic8800_fdrv-original.ko
        expected_bsp=a8ad26ea7466b520fc74a5a712cefbee76d42e371b87943026c116a8d46900c7
        expected_fdrv=96ac9fb52005ad33a4e0d900da8ad47539a976f4e86f161ff75ccccba946d5de
        ;;
    50mhz)
        source_dir=/var/backups/h96-wifi-25mhz-20261101
        source_bsp=$source_dir/aic8800_bsp-50mhz.ko
        source_fdrv=/home/nguyentiem/h96-wifi-candidate-20261101/aic8800_fdrv.ko
        expected_bsp=6529fad86a267a6e914db12fe5a3062054ceb00ae82434d9d703def2cea3064f
        expected_fdrv=e6dd598ec10e711763eeee3b094036fddc180318da6ac4de436b4df1be637ced
        ;;
    *)
        echo 'Usage: restore-aic8801-modules.sh original|50mhz' >&2
        exit 2
        ;;
esac

check_hash() {
    [[ $(sha256sum "$1" | cut -d' ' -f1) == "$2" ]] || {
        echo "SHA-256 mismatch: $1" >&2
        exit 1
    }
}
check_hash "$source_bsp" "$expected_bsp"
check_hash "$source_fdrv" "$expected_fdrv"

bsp=$(/sbin/modinfo -n aic8800_bsp)
fdrv=$(/sbin/modinfo -n aic8800_fdrv)
install -m 0644 "$source_bsp" "${bsp}.h96-restore"
install -m 0644 "$source_fdrv" "${fdrv}.h96-restore"
mv -f "${bsp}.h96-restore" "$bsp"
mv -f "${fdrv}.h96-restore" "$fdrv"
/sbin/depmod -a
check_hash "$bsp" "$expected_bsp"
check_hash "$fdrv" "$expected_fdrv"
sync
echo "Restored $mode modules on SD. Cold boot required; running modules are unchanged."
