#!/usr/bin/env bash
# Build the AIC8801 SDIO driver from a pinned source revision.

declare -g H96_AIC_REPO="https://github.com/queenkjuul/aic8800-milkv-duos"
declare -g H96_AIC_REF="commit:ccf8fd059f70384fae4878c1048603510c2df700"
declare -g H96_AIC_FW_DIR="/lib/firmware/aic8800/SDIO/aic8800D80"

function extension_prepare_config__h96max_aic8801_packages() {
	add_packages_to_image bluez rfkill
}

function post_family_config__h96max_aic8801_src_dir() {
	declare -g H96_AIC_SRC_DIR="${SRC}/cache/sources/aic8800-milkv-duos/${H96_AIC_REF#*:}"
}

function custom_kernel_config__h96max_aic8801_modules() {
	declare -a patches=()
	mapfile -t patches < <(find "${SRC}/patch/misc/aic8800" -maxdepth 1 -name '*.patch' | sort)
	kernel_config_modifying_hashes+=("h96max_aic8801=${H96_AIC_REF}")
	kernel_config_modifying_hashes+=("h96max_aic8801_extension=$(sha256sum "${SRC}/extensions/h96max-aic8801.sh" | cut -d' ' -f1)")
	kernel_config_modifying_hashes+=("h96max_aic8801_patches=$(cat /dev/null "${patches[@]}" | sha256sum | cut -d' ' -f1)")
	kernel_config_modifying_hashes+=("h96max_aic8801_fw=${H96_AIC_FW_DIR}")
	[[ ! -f .config ]] && return 0

	declare kernel_cwd="${PWD}"
	fetch_from_repo "${H96_AIC_REPO}" "aic8800-milkv-duos" "${H96_AIC_REF}" "yes"
	cd "${kernel_cwd}" || exit_with_error "AIC8801" "cannot return to kernel tree"

	declare wireless_dir="${kernel_work_dir}/drivers/net/wireless"
	declare driver_dir="${wireless_dir}/aicsemi"
	run_host_command_logged rm -rf "${driver_dir}"
	run_host_command_logged mkdir -p "${driver_dir}"
	run_host_command_logged cp -a "${H96_AIC_SRC_DIR}/aicsemi/." "${driver_dir}/"

	declare patch_file
	for patch_file in "${patches[@]}"; do
		run_host_command_logged patch --batch -p1 -d "${kernel_work_dir}" "<" "${patch_file}" ||
			exit_with_error "AIC8801 patch failed" "$(basename "${patch_file}")"
	done

	# The pinned source defaults to CVITEK and uses APIs newer than vendor 6.1.
	sed -i 's/^export CONFIG_PLATFORM_CVITEK = y$/export CONFIG_PLATFORM_CVITEK = n/' \
		"${driver_dir}/aic8800/Makefile"
	find "${driver_dir}/aic8800" -name '*.c' -exec sed -i \
		's/timer_container_of(/from_timer(/g' {} +
	sed -i 's/const void \*data)/void *data)/' \
		"${driver_dir}/aic8800/aic8800_bsp/aicsdio.c"
	sed -i 's/rwnx_cfg80211_set_monitor_channel(wiphy, NULL, NULL)/rwnx_cfg80211_set_monitor_channel(wiphy, NULL)/' \
		"${driver_dir}/aic8800/aic8800_fdrv/rwnx_main.c"

	sed -i "s|^CONFIG_AIC_FW_PATH = .*|CONFIG_AIC_FW_PATH = \"${H96_AIC_FW_DIR}\"|" \
		"${driver_dir}/aic8800/aic8800_bsp/Makefile"
	grep -qF "CONFIG_AIC_FW_PATH = \"${H96_AIC_FW_DIR}\"" \
		"${driver_dir}/aic8800/aic8800_bsp/Makefile" ||
		exit_with_error "AIC8801 firmware path mismatch" "${H96_AIC_FW_DIR}"

	if ! grep -q 'aicsemi/Kconfig' "${wireless_dir}/Kconfig"; then
		sed -i 's|^source "drivers/net/wireless/admtek/Kconfig"|source "drivers/net/wireless/aicsemi/Kconfig"\n&|' \
			"${wireless_dir}/Kconfig"
	fi
	if ! grep -q 'aicsemi/' "${wireless_dir}/Makefile"; then
		echo 'obj-$(CONFIG_WLAN_VENDOR_AICSEMI) += aicsemi/' >> "${wireless_dir}/Makefile"
	fi

	kernel_config_set_y CONFIG_WLAN_VENDOR_AICSEMI
	kernel_config_set_y CONFIG_AIC8800
	kernel_config_set_string CONFIG_AIC_FW_PATH "${H96_AIC_FW_DIR}"
	kernel_config_set_m CONFIG_CFG80211
}

function post_customize_image__h96max_aic8801_firmware() {
	declare fw_dir="${SDCARD}${H96_AIC_FW_DIR}"
	declare fw_file
	for fw_file in fw_adid.bin fw_patch.bin fw_patch_table.bin fmacfw.bin aic_userconfig.txt; do
		[[ -f "${fw_dir}/${fw_file}" ]] ||
			exit_with_error "AIC8801 firmware missing" "${fw_dir}/${fw_file}"
	done

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
[ -e /dev/ttyS2 ] || exit 1
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
	chroot_sdcard systemctl --no-reload enable h96max-bluetooth.service
}
