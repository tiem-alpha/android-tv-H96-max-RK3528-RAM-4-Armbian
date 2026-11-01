#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
build_dir="${repo_dir}/armbian-build"

if [[ ! -x "${build_dir}/compile.sh" ]]; then
	echo "Missing ${build_dir}/compile.sh" >&2
	exit 1
fi

if [[ "$(uname -m)" != "aarch64" ]]; then
	command -v docker >/dev/null || { echo "Docker is required for ARM64 build" >&2; exit 1; }
	if [[ ! -r /proc/sys/fs/binfmt_misc/qemu-aarch64 ]] ||
		! grep -q '^enabled$' /proc/sys/fs/binfmt_misc/qemu-aarch64; then
		echo "Registering ARM64 QEMU/binfmt on the host"
		docker run --privileged --rm tonistiigi/binfmt --install arm64
	fi
fi

for file in \
	"${repo_dir}/patches/extensions/h96max-aic8801.sh" \
	"${repo_dir}/patches/patch/u-boot/legacy/u-boot-radxa-rk35xx/defconfig/hinlink_rk3528_defconfig" \
	"${repo_dir}/patches/patch/kernel/rk35xx-vendor-6.1/dt/rk3528-h96max-stock-rails-net-hdmi.dts"; do
	[[ -s "${file}" ]] || { echo "Missing ${file}" >&2; exit 1; }
done

for firmware in fw_adid.bin fw_patch.bin fw_patch_table.bin fmacfw.bin aic_userconfig.txt; do
	file="${repo_dir}/patches/userpatches/overlay/lib/firmware/aic8800/SDIO/aic8800D80/${firmware}"
	[[ -s "${file}" ]] || { echo "Missing ${file}" >&2; exit 1; }
done

cp -a "${repo_dir}/patches/." "${build_dir}/"

threads="${H96_BUILD_THREADS:-8}"
[[ "${threads}" =~ ^[1-9][0-9]*$ ]] || { echo "H96_BUILD_THREADS must be a positive integer" >&2; exit 1; }

cd "${build_dir}"
CPUTHREADS="${threads}" ./compile.sh build \
	BOARD=rk3528-h96max \
	BRANCH=vendor \
	BUILD_MINIMAL=no \
	BUILD_DESKTOP=yes \
	DESKTOP_ENVIRONMENT=xfce \
	DESKTOP_TIER=mid \
	RELEASE=trixie \
	KERNEL_CONFIGURE=no \
	KERNEL_GIT=shallow
