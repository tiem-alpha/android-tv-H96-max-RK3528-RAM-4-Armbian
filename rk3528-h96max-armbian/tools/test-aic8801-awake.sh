#!/bin/bash
set -euo pipefail
export PATH=/usr/sbin:/usr/bin:/sbin:/bin

candidate=/boot/h96-wifi-test/aic8800_bsp-awake-matched.ko
expected_candidate=b25c7caaa23ba360640b19c46486d1ffe6f8363911c9f4a7bec5b12aaf32447f
expected_original=a8ad26ea7466b520fc74a5a712cefbee76d42e371b87943026c116a8d46900c7
logdir=/var/log/h96-wifi-test-$(date +%Y%m%d-%H%M%S)
timer=h96-wifi-rollback

[[ $(id -u) == 0 ]] || { echo 'Run as root'; exit 1; }
[[ $(uname -r) == 6.1.172-vendor-rk35xx ]] || { echo 'Unexpected kernel'; exit 1; }
[[ -f $candidate ]] || { echo "Missing $candidate"; exit 1; }
[[ $(sha256sum "$candidate" | cut -d' ' -f1) == "$expected_candidate" ]] || { echo 'Candidate hash mismatch'; exit 1; }
[[ $(modinfo -F vermagic "$candidate" | cut -d' ' -f1) == $(uname -r) ]] || { echo 'Candidate vermagic mismatch'; exit 1; }
original=$(modinfo -n aic8800_bsp)
[[ $(sha256sum "$original" | cut -d' ' -f1) == "$expected_original" ]] || { echo 'Original module hash mismatch'; exit 1; }

mkdir -p "$logdir"
cp "$original" "$logdir/original-aic8800_bsp.ko"
dmesg > "$logdir/dmesg-before.txt"
lsmod | grep aic8800 > "$logdir/modules-before.txt" || true

cat > "$logdir/rollback.sh" <<'EOF'
#!/bin/bash
set +e
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
nmcli radio wifi off
modprobe -r aic8800_fdrv
modprobe -r aic8800_bsp
modprobe aic8800_bsp
modprobe aic8800_fdrv
nmcli radio wifi on
EOF
chmod 700 "$logdir/rollback.sh"
systemd-run --unit="$timer" --on-active=180s /bin/bash "$logdir/rollback.sh"
trap '/bin/bash "$logdir/rollback.sh"; systemctl stop "$timer.timer" 2>/dev/null || true' EXIT

nmcli radio wifi off
modprobe -r aic8800_fdrv
modprobe -r aic8800_bsp
insmod "$candidate"
modprobe aic8800_fdrv
nmcli radio wifi on
sleep 5
timeout 45s iw dev wlan0 scan > "$logdir/scan.txt" 2> "$logdir/scan-error.txt" || true
ip addr show wlan0 > "$logdir/wlan0.txt"
lsmod | grep aic8800 > "$logdir/modules-test.txt" || true
dmesg > "$logdir/dmesg-test.txt"
echo "Result: $logdir"
