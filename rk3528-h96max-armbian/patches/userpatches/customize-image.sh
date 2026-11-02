#!/bin/bash
set -e

# Armbian runs this inside the target rootfs; overlay is supplied by the build.
source /tmp/overlay/h96-radio.conf
gtx_fw="/tmp/overlay${H96_AIC_FW_DIR}"
[[ -s "$gtx_fw/SHA256SUMS" ]] || { echo "Missing GTX firmware: $gtx_fw" >&2; exit 1; }
(cd "$gtx_fw" && sha256sum -c SHA256SUMS)
mkdir -p "${H96_AIC_FW_DIR}"
cp -a "$gtx_fw"/. "${H96_AIC_FW_DIR}/"
# Keep GPIO38 high; LED state restore generated a pulse that broke Wi-Fi.
mkdir -p /etc/systemd/system
ln -sfn /dev/null /etc/systemd/system/armbian-led-state.service

led_files=/tmp/overlay/h96-fd655

if [[ ! -d "$led_files" ]]; then
	echo "Missing FD655 LED overlay: $led_files" >&2
	exit 1
fi

	for file in h96-fd655.py h96-fd655.service h96-fd655.json; do
		[[ -s "$led_files/$file" ]] || { echo "Missing FD655 LED file: $file" >&2; exit 1; }
	done
	install -Dm755 "$led_files/h96-fd655.py" /usr/local/lib/h96-fd655.py
	install -Dm644 "$led_files/h96-fd655.service" /etc/systemd/system/h96-fd655.service
	install -Dm644 "$led_files/h96-fd655.json" /etc/h96-fd655.json
	mkdir -p /etc/systemd/system/multi-user.target.wants
	ln -sfn /etc/systemd/system/h96-fd655.service \
		/etc/systemd/system/multi-user.target.wants/h96-fd655.service
