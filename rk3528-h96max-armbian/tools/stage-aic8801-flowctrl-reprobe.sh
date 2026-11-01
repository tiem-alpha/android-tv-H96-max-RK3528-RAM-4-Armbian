#!/bin/bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin

[[ $(id -u) == 0 ]] || { echo 'Run as root' >&2; exit 1; }
[[ $(uname -r) == 6.1.172-vendor-rk35xx ]] || { echo 'Unexpected kernel' >&2; exit 1; }

candidate_dir=/home/nguyentiem/h96-wifi-candidate-20261101
backup_dir=/var/backups/h96-wifi-flowctrl-20261101
bsp=$(/sbin/modinfo -n aic8800_bsp)
fdrv=$(/sbin/modinfo -n aic8800_fdrv)

check_hash() {
    [[ $(sha256sum "$1" | cut -d' ' -f1) == "$2" ]] || {
        echo "SHA-256 mismatch: $1" >&2
        exit 1
    }
}

check_hash "$bsp" a8ad26ea7466b520fc74a5a712cefbee76d42e371b87943026c116a8d46900c7
check_hash "$fdrv" 96ac9fb52005ad33a4e0d900da8ad47539a976f4e86f161ff75ccccba946d5de
check_hash "$candidate_dir/aic8800_bsp.ko" 6529fad86a267a6e914db12fe5a3062054ceb00ae82434d9d703def2cea3064f
check_hash "$candidate_dir/aic8800_fdrv.ko" e6dd598ec10e711763eeee3b094036fddc180318da6ac4de436b4df1be637ced

[[ $(/sbin/modinfo -F vermagic "$candidate_dir/aic8800_bsp.ko" | cut -d' ' -f1) == $(uname -r) ]]
[[ $(/sbin/modinfo -F vermagic "$candidate_dir/aic8800_fdrv.ko" | cut -d' ' -f1) == $(uname -r) ]]
[[ ! -e "$backup_dir" ]] || { echo "Backup exists: $backup_dir" >&2; exit 1; }

install -d -m 0755 "$backup_dir"
install -m 0644 "$bsp" "$backup_dir/aic8800_bsp-original.ko"
install -m 0644 "$fdrv" "$backup_dir/aic8800_fdrv-original.ko"
check_hash "$backup_dir/aic8800_bsp-original.ko" a8ad26ea7466b520fc74a5a712cefbee76d42e371b87943026c116a8d46900c7
check_hash "$backup_dir/aic8800_fdrv-original.ko" 96ac9fb52005ad33a4e0d900da8ad47539a976f4e86f161ff75ccccba946d5de
printf '%s\n' "$bsp" "$fdrv" > "$backup_dir/module-paths.txt"

rollback() {
    trap - ERR
    install -m 0644 "$backup_dir/aic8800_bsp-original.ko" "$bsp"
    install -m 0644 "$backup_dir/aic8800_fdrv-original.ko" "$fdrv"
    /sbin/depmod -a
    sync
    echo 'Stage failed; restored both original modules.' >&2
}
trap rollback ERR

install -m 0644 "$candidate_dir/aic8800_bsp.ko" "${bsp}.h96-new"
install -m 0644 "$candidate_dir/aic8800_fdrv.ko" "${fdrv}.h96-new"
mv -f "${bsp}.h96-new" "$bsp"
mv -f "${fdrv}.h96-new" "$fdrv"
/sbin/depmod -a
check_hash "$bsp" 6529fad86a267a6e914db12fe5a3062054ceb00ae82434d9d703def2cea3064f
check_hash "$fdrv" e6dd598ec10e711763eeee3b094036fddc180318da6ac4de436b4df1be637ced
sync
trap - ERR
echo "Staged BSP/FDRV; backups: $backup_dir"
echo 'Cold boot required. No running module or boot service was changed.'
