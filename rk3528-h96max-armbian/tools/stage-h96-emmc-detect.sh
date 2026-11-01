#!/bin/bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
[[ $(id -u) == 0 ]] || { echo 'Run as root' >&2; exit 1; }
[[ $(uname -r) == 6.1.172-vendor-rk35xx ]] || exit 1
candidate=/home/nguyentiem/h96-wifi-25mhz-20261101/emmc-enabled-from-baseline.dtb
target=/boot/dtb/rockchip/rk3528-h96max-stock-rails-net-hdmi-wifi32k.dtb
backup=/var/backups/h96-emmc-detect-20261101/baseline.dtb
basehash=ca21b5d1031287a0d01e7bb09419397642f1f97fbffd4d7f6f620281a4e688ee
newhash=593d8046ca068e8958cd196725e624160bcefa8fac5eda9f7ab447c2854e4827
check() { [[ $(sha256sum "$1" | cut -d' ' -f1) == "$2" ]] || { echo "SHA mismatch: $1" >&2; exit 1; }; }
check "$candidate" "$newhash"
check "$target" "$basehash"
mkdir -p "$(dirname "$backup")"
if [[ ! -e "$backup" ]]; then install -m 0644 "$target" "$backup"; fi
check "$backup" "$basehash"
install -m 0644 "$candidate" "${target}.h96-new"
mv -f "${target}.h96-new" "$target"
check "$target" "$newhash"
sync
echo "eMMC detection DTB staged; restore from $backup if boot fails."
