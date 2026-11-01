#!/bin/bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin

candidate=/home/nguyentiem/aic8800_bsp-no-sdio-pwrctrl.ko
candidate_sha=da0aae04ab6f8b611d681d7524774a151daa1261cf6173e1ddec8c9732e6e3bc
original_sha=a8ad26ea7466b520fc74a5a712cefbee76d42e371b87943026c116a8d46900c7
fdrv_sha=96ac9fb52005ad33a4e0d900da8ad47539a976f4e86f161ff75ccccba946d5de
backup_dir=/var/backups/h96-wifi-oneboot
restore=/usr/local/sbin/h96-wifi-oneboot-restore
service=/etc/systemd/system/h96-wifi-oneboot-restore.service

[[ $(id -u) == 0 ]] || { echo 'Run as root'; exit 1; }
[[ $(uname -r) == 6.1.172-vendor-rk35xx ]] || { echo 'Unexpected kernel'; exit 1; }
original=$(modinfo -n aic8800_bsp)
fdrv=$(modinfo -n aic8800_fdrv)
[[ $(sha256sum "$original" | cut -d' ' -f1) == "$original_sha" ]] || { echo 'Original BSP hash mismatch'; exit 1; }
[[ $(sha256sum "$fdrv" | cut -d' ' -f1) == "$fdrv_sha" ]] || { echo 'FDRV hash mismatch'; exit 1; }
[[ $(sha256sum "$candidate" | cut -d' ' -f1) == "$candidate_sha" ]] || { echo 'Candidate hash mismatch'; exit 1; }
[[ $(modinfo -F vermagic "$candidate" | cut -d' ' -f1) == $(uname -r) ]] || { echo 'Candidate vermagic mismatch'; exit 1; }

install -d -m 0755 "$backup_dir"
install -m 0644 "$original" "$backup_dir/aic8800_bsp-original.ko"
trap 'trap - ERR; install -m 0644 "$backup_dir/aic8800_bsp-original.ko" "$original"; depmod -a; systemctl disable h96-wifi-oneboot-restore.service' ERR
cat > "$restore" <<EOF
#!/bin/bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
sleep 180
dmesg > "$backup_dir/dmesg-test.txt"
lsmod > "$backup_dir/lsmod-test.txt"
install -m 0644 "$backup_dir/aic8800_bsp-original.ko" "$original"
depmod -a
systemctl disable h96-wifi-oneboot-restore.service
date -Is > "$backup_dir/restored-at.txt"
EOF
chmod 0755 "$restore"
cat > "$service" <<'EOF'
[Unit]
Description=Restore original AIC8801 BSP after one boot test
After=systemd-modules-load.service

[Service]
Type=oneshot
ExecStart=/bin/bash /usr/local/sbin/h96-wifi-oneboot-restore
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable h96-wifi-oneboot-restore.service
install -m 0644 "$candidate" "${original}.h96-test-tmp"
mv -f "${original}.h96-test-tmp" "$original"
depmod -a
trap - ERR
echo "Staged BSP: $(sha256sum "$original")"
echo "Saved BSP:  $(sha256sum "$backup_dir/aic8800_bsp-original.ko")"
echo 'Power off completely. Wait 10 seconds. Then boot Armbian from SD.'
