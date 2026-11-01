#!/bin/bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin

[[ $(id -u) == 0 ]] || { echo 'Run as root' >&2; exit 1; }
[[ $(uname -r) == 6.1.172-vendor-rk35xx ]] || { echo 'Unexpected kernel' >&2; exit 1; }

mode=${1:-}
case "$mode" in
    1bit)
        name=sdio-1bit.dtb
        expected=ee622ee9685c2e3de8421b801d71a2ead4d1084e8190e83dd958e5bc2dcf7ff4
        ;;
    delay200)
        name=pwrseq-delay-200ms.dtb
        expected=0d9095021c6d8d4a4edca2b33a82315be3bf52511b2d8c97107e02bf0a12c998
        ;;
    polling)
        name=sdio-polling-no-nonremovable.dtb
        expected=526ed8531a1d446b97faee2923c665d3a23b1efd67369a35c1d82c58e7903526
        ;;
    androidwifi)
        name=android-wifi-match.dtb
        expected=2900b5df495ca78ee7b3f45ca966314d72fd8b096f3f9fe0e6815113c445022f
        ;;
    baseline)
        name=baseline.dtb
        expected=ca21b5d1031287a0d01e7bb09419397642f1f97fbffd4d7f6f620281a4e688ee
        ;;
    *)
        echo 'Usage: stage-aic8801-dtb-variant.sh baseline|1bit|delay200|polling|androidwifi' >&2
        exit 2
        ;;
esac

candidate=/home/nguyentiem/h96-wifi-25mhz-20261101/$name
target=/boot/dtb/rockchip/rk3528-h96max-stock-rails-net-hdmi-wifi32k.dtb
backup=/var/backups/h96-wifi-dtb-baseline-20261101.dtb
baseline_hash=ca21b5d1031287a0d01e7bb09419397642f1f97fbffd4d7f6f620281a4e688ee

[[ $(sha256sum "$candidate" | cut -d' ' -f1) == "$expected" ]] || {
    echo "Candidate hash mismatch: $candidate" >&2; exit 1;
}
if [[ ! -e "$backup" ]]; then
    [[ $(sha256sum "$target" | cut -d' ' -f1) == "$baseline_hash" ]] || {
        echo 'Current DTB is not baseline; refusing to create backup' >&2; exit 1;
    }
    install -m 0644 "$target" "$backup"
fi
[[ $(sha256sum "$backup" | cut -d' ' -f1) == "$baseline_hash" ]] || {
    echo 'Baseline backup hash mismatch' >&2; exit 1;
}

install -m 0644 "$candidate" "${target}.h96-new"
mv -f "${target}.h96-new" "$target"
[[ $(sha256sum "$target" | cut -d' ' -f1) == "$expected" ]]
sync
echo "Staged DTB $mode; baseline backup: $backup"
echo 'Cold boot required. Module files and boot services were not changed.'
