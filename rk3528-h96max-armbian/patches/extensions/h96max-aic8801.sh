#!/usr/bin/env bash
# Build the AIC8801 SDIO driver from a pinned source revision.

source "${SRC}/config/h96-aic8800.conf"

function extension_prepare_config__h96max_aic8801_packages() {
	add_packages_to_image bluez rfkill python3-libgpiod
}

function post_family_config__h96max_aic8801_src_dir() {
	declare -g H96_AIC_SRC_DIR="${SRC}/cache/sources/aic8800-gtx/${H96_AIC_COMMIT}"
}

function custom_kernel_config__h96max_aic8801_modules() {
	declare -a patches=()
	mapfile -t patches < <(find "${SRC}/patch/misc/aic8800-gtx" -maxdepth 1 -name '*.patch' | sort)
	[[ ${#patches[@]} -eq 2 ]] || exit_with_error "AIC8801 patches missing" "expected two GTX port patches"
	kernel_config_modifying_hashes+=("h96max_aic8801=${H96_AIC_REF}")
	kernel_config_modifying_hashes+=("h96max_aic8801_extension=$(sha256sum "${SRC}/extensions/h96max-aic8801.sh" | cut -d' ' -f1)")
	kernel_config_modifying_hashes+=("h96max_aic8801_patches=$(cat /dev/null "${patches[@]}" | sha256sum | cut -d' ' -f1)")
	kernel_config_modifying_hashes+=("h96max_aic8801_fw=${H96_AIC_FW_DIR}")
	kernel_config_modifying_hashes+=("h96max_aic8801_lock=$(sha256sum "${SRC}/config/h96-aic8800.conf" | cut -d' ' -f1)")
	kernel_config_modifying_hashes+=("h96max_aic8801_firmware=$(sha256sum "${SRC}/config/h96-aic8800-firmware.sha256" | cut -d' ' -f1)")
	[[ ! -f .config ]] && return 0

	declare kernel_cwd="${PWD}"
	fetch_from_repo "${H96_AIC_REPO}" "aic8800-gtx" "${H96_AIC_REF}" "yes"
	cd "${kernel_cwd}" || exit_with_error "AIC8801" "cannot return to kernel tree"

	declare wireless_dir="${kernel_work_dir}/drivers/net/wireless"
	declare driver_dir="${wireless_dir}/aicsemi"
	run_host_command_logged rm -rf "${driver_dir}"
	run_host_command_logged mkdir -p "${driver_dir}"
	run_host_command_logged mkdir -p "${driver_dir}/aic8800"
	run_host_command_logged cp -a "${H96_AIC_SRC_DIR}/${H96_AIC_DRIVER_SUBDIR}/." "${driver_dir}/aic8800/"

	declare patch_file
	for patch_file in "${patches[@]}"; do
		run_host_command_logged patch --batch -p1 -d "${driver_dir}/aic8800" "<" "${patch_file}" ||
			exit_with_error "AIC8801 patch failed" "$(basename "${patch_file}")"
	done

	cat > "${driver_dir}/Kconfig" <<'EOF'
config WLAN_VENDOR_AICSEMI
	bool "AICSEMI devices"
	default n
if WLAN_VENDOR_AICSEMI
source "drivers/net/wireless/aicsemi/aic8800/Kconfig"
endif
EOF
	printf '%s\n' 'obj-$(CONFIG_AIC_WLAN_SUPPORT) += aic8800/' > "${driver_dir}/Makefile"
	sed -i 's|drivers/net/wireless/aic8800/|drivers/net/wireless/aicsemi/aic8800/|g' "${driver_dir}/aic8800/Kconfig"
	grep -qF "#define AICBSP_FW_PATH              \"${H96_AIC_FW_DIR}\"" "${driver_dir}/aic8800/aic8800_bsp/aic_bsp_driver.h" ||
		exit_with_error "AIC8801 firmware path mismatch" "${H96_AIC_FW_DIR}"
	grep -q '^export CONFIG_PREALLOC_RX_SKB = y$' "${driver_dir}/aic8800/Makefile" ||
		exit_with_error "AIC8801 RX config mismatch" "CONFIG_PREALLOC_RX_SKB"

	if ! grep -q 'aicsemi/Kconfig' "${wireless_dir}/Kconfig"; then
		printf '\nsource "drivers/net/wireless/aicsemi/Kconfig"\n' >> "${wireless_dir}/Kconfig"
	fi
	if ! grep -q 'aicsemi/' "${wireless_dir}/Makefile"; then
		echo 'obj-$(CONFIG_WLAN_VENDOR_AICSEMI) += aicsemi/' >> "${wireless_dir}/Makefile"
	fi

	kernel_config_set_y CONFIG_WLAN_VENDOR_AICSEMI
	kernel_config_set_y CONFIG_AIC_WLAN_SUPPORT
	kernel_config_set_m CONFIG_AIC8800_WLAN_SUPPORT
	kernel_config_set_m CONFIG_AIC8800_BTLPM_SUPPORT
	kernel_config_set_string CONFIG_AIC_FW_PATH "${H96_AIC_FW_DIR}"
	kernel_config_set_m CONFIG_CFG80211
}

function post_customize_image__h96max_aic8801_firmware() {
	declare fw_dir="${SDCARD}${H96_AIC_FW_DIR}"
	[[ -s "${fw_dir}/SHA256SUMS" ]] || exit_with_error "AIC firmware manifest missing" "${fw_dir}"
	(cd "${fw_dir}" && sha256sum -c "${SRC}/config/h96-aic8800-firmware.sha256") ||
		exit_with_error "AIC firmware verification failed" "${fw_dir}"
	mkdir -p "${SDCARD}/etc/systemd/system"
	# Prevent the LED restore pulse on GPIO38 found in the paired boot traces.
	ln -sfn /dev/null "${SDCARD}/etc/systemd/system/armbian-led-state.service"

	mkdir -p "${SDCARD}/etc/modprobe.d" "${SDCARD}/etc/modules-load.d"
	printf '%s\n' 'softdep aic8800_fdrv pre: aic8800_bsp' > \
		"${SDCARD}/etc/modprobe.d/aic8801.conf"
	printf '%s\n' aic8800_bsp aic8800_fdrv > \
		"${SDCARD}/etc/modules-load.d/aic8801.conf"

	install -d -m 0755 "${SDCARD}/usr/local/sbin" "${SDCARD}/etc/systemd/system"
	cat > "${SDCARD}/usr/local/sbin/h96max-bluetooth" <<'EOF'
#!/bin/sh
set -eu

# The Android DTB routes Bluetooth to UART2; its firmware selects 1.5 Mbaud.
for attempt in 1 2 3 4 5; do
	[ -e /dev/ttyS2 ] && [ -d /sys/module/aic8800_bsp ] && break
	sleep 2
done
[ -e /dev/ttyS2 ] && [ -d /sys/module/aic8800_bsp ] || exit 1
# Unblock the Rockchip Bluetooth radio before UART HCI attach.
rfkill unblock bluetooth
exec hciattach -n -s 1500000 /dev/ttyS2 any 1500000 flow nosleep
EOF
	chmod 0755 "${SDCARD}/usr/local/sbin/h96max-bluetooth"
	cat > "${SDCARD}/etc/systemd/system/h96max-bluetooth.service" <<'EOF'
[Unit]
Description=H96 Max AIC8801 Bluetooth UART
After=systemd-modules-load.service
Wants=bluetooth.service
Before=bluetooth.service

[Service]
Type=simple
ExecStart=/usr/local/sbin/h96max-bluetooth
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
	mkdir -p "${SDCARD}/etc/bluetooth"
	python3 - "${SDCARD}/etc/bluetooth/main.conf" <<'PYCFG'
from pathlib import Path
import re, sys
p = Path(sys.argv[1])
s = p.read_text() if p.exists() else ""
section = re.search(r"(?ms)^\[Policy\][ \t]*\n(.*?)(?=^\[|\Z)", s)
if section:
    policy = re.sub(r"(?m)^\s*#?\s*AutoEnable\s*=.*\n?", "", section.group(1))
    s = s[:section.start(1)] + "AutoEnable=true\n" + policy + s[section.end(1):]
else:
    s += "\n[Policy]\nAutoEnable=true\n"
p.write_text(s)
PYCFG
	chroot_sdcard systemctl --no-reload enable h96max-bluetooth.service bluetooth.service
	cat > "${SDCARD}/etc/h96-radio-build.conf" <<EOF
SOURCE_REPO=${H96_AIC_REPO}
SOURCE_COMMIT=${H96_AIC_COMMIT}
SOURCE_DRIVER=${H96_AIC_DRIVER_SUBDIR}
FIRMWARE_DIR=${H96_AIC_FW_DIR}
RX_PREALLOCATION=y
SDIO_POWER_CONTROL=y
SDIO_CLOCK=50000000
GPIO38_LED_RESTORE=masked
BLUETOOTH_UART=/dev/ttyS2
BLUETOOTH_BAUD=1500000
EOF
}
