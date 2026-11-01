#!/bin/bash
set -e

# Armbian runs this inside the target rootfs; overlay is supplied by the build.
factory_fw=/tmp/overlay/lib/firmware/aic8800/SDIO/aic8800D80
if [[ -d "$factory_fw" ]]; then
	mkdir -p /lib/firmware/aic8800/SDIO/aic8800D80
	cp -a "$factory_fw"/. /lib/firmware/aic8800/SDIO/aic8800D80/
fi
