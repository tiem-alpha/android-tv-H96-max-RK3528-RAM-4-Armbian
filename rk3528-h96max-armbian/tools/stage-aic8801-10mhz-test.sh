#!/bin/bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin

[[ $(id -u) == 0 ]] || { echo 'Run as root' >&2; exit 1; }
[[ $(uname -r) == 6.1.172-vendor-rk35xx ]] || { echo 'Unexpected kernel' >&2; exit 1; }

candidate=/home/nguyentiem/h96-wifi-25mhz-20261101/aic8800_bsp-10mhz.ko
backup_dir=/var/backups/h96-wifi-10mhz-20261101
bsp=$(/sbin/modinfo -n aic8800_bsp)
fdrv=$(/sbin/modinfo -n aic8800_fdrv)

check_hash() {
    [[ $(sha256sum "$1" | cut -d' ' -f1) == "$2" ]] || {
        echo "SHA-256 mismatch: $1" >&2
        exit 1
    }
}

check_hash "$bsp" ce23114d5e2f79dc3f7cfe6fced25da93bac29c01d3cf8b34a64f3aa1ca73a5c
check_hash "$fdrv" e6dd598ec10e711763eeee3b094036fddc180318da6ac4de436b4df1be637ced
check_hash "$candidate" de0c2ad395e3e6417363cf1a581a9f519c6420a57dc83fea13081e2a5666bdd5
[[ $(/sbin/modinfo -F vermagic "$candidate" | cut -d' ' -f1) == $(uname -r) ]]
[[ ! -e "$backup_dir" ]] || { echo "Backup exists: $backup_dir" >&2; exit 1; }

install -d -m 0755 "$backup_dir"
install -m 0644 "$bsp" "$backup_dir/aic8800_bsp-25mhz.ko"
check_hash "$backup_dir/aic8800_bsp-25mhz.ko" ce23114d5e2f79dc3f7cfe6fced25da93bac29c01d3cf8b34a64f3aa1ca73a5c
printf '%s\n' "$bsp" > "$backup_dir/module-path.txt"

rollback() {
    trap - ERR
    install -m 0644 "$backup_dir/aic8800_bsp-25mhz.ko" "$bsp"
    /sbin/depmod -a
    sync
    echo 'Stage failed; restored 25 MHz BSP.' >&2
}
trap rollback ERR

install -m 0644 "$candidate" "${bsp}.h96-new"
mv -f "${bsp}.h96-new" "$bsp"
/sbin/depmod -a
check_hash "$bsp" de0c2ad395e3e6417363cf1a581a9f519c6420a57dc83fea13081e2a5666bdd5
sync
trap - ERR
echo "Staged 10 MHz BSP; backup: $backup_dir"
echo 'Cold boot required. FDRV and boot services were not changed.'
