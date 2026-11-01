#!/bin/bash
set -e

# Armbian runs this inside the target rootfs; overlay is supplied by the build.
factory_fw=/tmp/overlay/lib/firmware/aic8800/SDIO/aic8800D80
if [[ -d "$factory_fw" ]]; then
	mkdir -p /lib/firmware/aic8800/SDIO/aic8800D80
	cp -a "$factory_fw"/. /lib/firmware/aic8800/SDIO/aic8800D80/
fi

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
