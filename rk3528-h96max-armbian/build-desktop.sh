#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
build_dir="${repo_dir}/armbian-build"

if [[ ! -x "${build_dir}/compile.sh" ]]; then
	echo "Missing ${build_dir}/compile.sh" >&2
	exit 1
fi

if [[ $(git -C "${build_dir}" rev-parse --show-toplevel 2>/dev/null || true) != "${build_dir}" ]]; then
	echo "${build_dir} is not an Armbian Git checkout; clone armbian/build there first." >&2
	exit 1
fi

# Prepare the exact same firmware revision as the kernel driver, automatically.
bash "${repo_dir}/tools/prepare-aic8800-gtx.sh"

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

source "${repo_dir}/patches/config/h96-aic8800.conf"
(cd "${repo_dir}/patches/userpatches/overlay${H96_AIC_FW_DIR}" && sha256sum -c SHA256SUMS)

led_overlay="${repo_dir}/patches/userpatches/overlay/h96-fd655"
for file in h96-fd655.py h96-fd655.service h96-fd655.json; do
	[[ -s "${repo_dir}/led/${file}" ]] || { echo "Missing LED file: ${repo_dir}/led/${file}" >&2; exit 1; }
done
mkdir -p "${led_overlay}"
install -m 0755 "${repo_dir}/led/h96-fd655.py" "${led_overlay}/h96-fd655.py"
install -m 0644 "${repo_dir}/led/h96-fd655.service" "${led_overlay}/h96-fd655.service"
install -m 0644 "${repo_dir}/led/h96-fd655.json" "${led_overlay}/h96-fd655.json"

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
