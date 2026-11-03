#!/usr/bin/env bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
(( EUID == 0 )) || { echo 'Run with sudo'; exit 1; }
backup=/var/backups/h96-wifi-before-nullguard-20261102
modules=/lib/modules/6.1.172-vendor-rk35xx/kernel/drivers/net/wireless/aicsemi/aic8800
(cd "$backup" && sha256sum -c SHA256SUMS)
install -m 0644 "$backup/aic8800_bsp.ko" "$modules/aic8800_bsp/"
install -m 0644 "$backup/aic8800_fdrv.ko" "$modules/aic8800_fdrv/"
depmod -a 6.1.172-vendor-rk35xx
sync
echo 'Previously bootable driver pair restored on disk. Boot again to load it.'
