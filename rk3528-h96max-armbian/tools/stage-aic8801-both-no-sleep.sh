#!/bin/bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin

bsp_candidate=/home/nguyentiem/aic8800_bsp-no-sdio-pwrctrl.ko
fdrv_candidate=/home/nguyentiem/aic8800_fdrv-no-sdio-pwrctrl.ko
bsp_candidate_sha=da0aae04ab6f8b611d681d7524774a151daa1261cf6173e1ddec8c9732e6e3bc
fdrv_candidate_sha=6d85cb4e7dd4b906c1d9e206b97af021e57f3fe8b246f21bcbb6e371224fe5c3
bsp_original_sha=a8ad26ea7466b520fc74a5a712cefbee76d42e371b87943026c116a8d46900c7
fdrv_original_sha=96ac9fb52005ad33a4e0d900da8ad47539a976f4e86f161ff75ccccba946d5de
backup_dir=/var/backups/h96-wifi-both-oneboot
restore=/usr/local/sbin/h96-wifi-both-oneboot-restore
service=/etc/systemd/system/h96-wifi-both-oneboot-restore.service

[[ $(id -u) == 0 ]] || { echo 'Run as root'; exit 1; }
[[ $(uname -r) == 6.1.172-vendor-rk35xx ]] || { echo 'Unexpected kernel'; exit 1; }
bsp=$(modinfo -n aic8800_bsp)
fdrv=$(modinfo -n aic8800_fdrv)
[[ $(sha256sum "$bsp" | cut -d' ' -f1) == "$bsp_original_sha" ]] || { echo 'Original BSP hash mismatch'; exit 1; }
[[ $(sha256sum "$fdrv" | cut -d' ' -f1) == "$fdrv_original_sha" ]] || { echo 'Original FDRV hash mismatch'; exit 1; }
[[ $(sha256sum "$bsp_candidate" | cut -d' ' -f1) == "$bsp_candidate_sha" ]] || { echo 'Candidate BSP hash mismatch'; exit 1; }
[[ $(sha256sum "$fdrv_candidate" | cut -d' ' -f1) == "$fdrv_candidate_sha" ]] || { echo 'Candidate FDRV hash mismatch'; exit 1; }
[[ $(modinfo -F vermagic "$bsp_candidate" | cut -d' ' -f1) == $(uname -r) ]] || { echo 'BSP vermagic mismatch'; exit 1; }
[[ $(modinfo -F vermagic "$fdrv_candidate" | cut -d' ' -f1) == $(uname -r) ]] || { echo 'FDRV vermagic mismatch'; exit 1; }

install -d -m 0755 "$backup_dir"
install -m 0644 "$bsp" "$backup_dir/aic8800_bsp-original.ko"
install -m 0644 "$fdrv" "$backup_dir/aic8800_fdrv-original.ko"
trap 'trap - ERR; install -m 0644 "$backup_dir/aic8800_bsp-original.ko" "$bsp"; install -m 0644 "$backup_dir/aic8800_fdrv-original.ko" "$fdrv"; depmod -a; systemctl disable h96-wifi-both-oneboot-restore.service' ERR
cat > "$restore" <<EOF
#!/bin/bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
sleep 180
dmesg > "$backup_dir/dmesg-test.txt"
lsmod > "$backup_dir/lsmod-test.txt"
install -m 0644 "$backup_dir/aic8800_bsp-original.ko" "$bsp"
install -m 0644 "$backup_dir/aic8800_fdrv-original.ko" "$fdrv"
depmod -a
systemctl disable h96-wifi-both-oneboot-restore.service
date -Is > "$backup_dir/restored-at.txt"
EOF
chmod 0755 "$restore"
cat > "$service" <<'EOF'
[Unit]
Description=Restore original AIC8801 modules after one boot test
After=systemd-modules-load.service

[Service]
Type=oneshot
ExecStart=/bin/bash /usr/local/sbin/h96-wifi-both-oneboot-restore
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable h96-wifi-both-oneboot-restore.service
install -m 0644 "$bsp_candidate" "${bsp}.h96-test-tmp"
install -m 0644 "$fdrv_candidate" "${fdrv}.h96-test-tmp"
mv -f "${bsp}.h96-test-tmp" "$bsp"
mv -f "${fdrv}.h96-test-tmp" "$fdrv"
depmod -a
trap - ERR
echo "Staged BSP:  $(sha256sum "$bsp")"
echo "Staged FDRV: $(sha256sum "$fdrv")"
echo 'Power off completely. Wait 10 seconds. Then boot Armbian from SD.'
