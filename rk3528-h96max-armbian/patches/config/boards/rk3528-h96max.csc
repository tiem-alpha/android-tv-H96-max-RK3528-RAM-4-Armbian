# SPDX-License-Identifier: GPL-2.0
#
# H96 Max RK3528 board layer for the vendor 6.1 kernel.

source "${SRC}/config/boards/hinlink-ht2.csc"
[[ ! -f "${SRC}/config/h96-local-build.conf" ]] || source "${SRC}/config/h96-local-build.conf"

BOARD_NAME="H96 Max RK3528"
BOARD_VENDOR="h96"
BOARD_MAINTAINER=""

# Stock PWM rails, integrated RMII/RK630 Ethernet, and HDMI VP0 routing.
BOOT_FDT_FILE="rockchip/rk3528-h96max-stock-rails-net-hdmi.dtb"
ENABLE_EXTENSIONS="h96max-aic8801"
