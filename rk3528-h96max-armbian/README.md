# H96 Max RK3528 Armbian patch

Hướng dẫn tiếng Việt từng bước: [Nhật ký và hướng dẫn build H96 Max RK3528](docs/HUONG_DAN_H96_MAX_RK3528.md).

Trạng thái đã kiểm chứng trên box và các lỗi còn tồn đọng: [nhật ký 31/10/2026](docs/TRANG_THAI_THUC_TE_2026-10-31.md).

Small overlay for building a minimal Armbian kernel image for the H96
Max RK3528. 

Working:

- boot from SD-card with stock firmware
- Ethernet
- HDMI
- others not tested

The [original stock Android boot log](logs/stock-boot.log) is included for hardware
comparison.

The full device tree extracted from the original boot image is included for
reference as [original-rk3528-evb2-ddr3-v10.dts](dts/original-rk3528-evb2-ddr3-v10.dts).

Board photos and UART port locations: https://forum.armbian.com/topic/59122-h96-max-rk3528-cannot-boot-armbian-from-tfsd-card/

## Build

For the AIC8801 Wi-Fi module found in this particular box, capture its factory
firmware while Android is running and ADB is connected:

    python3 tools/capture-aic-firmware.py

The copied firmware is ignored by Git and is installed in the image by
`userpatches/customize-image.sh`. Re-copy `patches/` into the Armbian checkout
after changing this repository. The board DTS disables the eMMC controller;
build and write the image to an SD card only. Do not use `armbian-install` or
any eMMC flashing tool on this test image.

The board wiring was checked against the running Android DTB from an RK3528
EVB2 DDR3 V10 box. The live Wi-Fi device reports SDIO vendor `0x5449`, device
`0x0145` (AIC8801), and Android loads AIC8800-family modules, despite the DTB's old `ap6275s`
label. HDMI, composite video, analog audio, USB power, Wi-Fi reset and LED
nodes have been aligned with that DTB. Hardware operation still requires a
successful boot and device-by-device checks; Bluetooth and AV output are not
verified on Linux yet.

Clone this repository, then run the following from its root directory.  The
upstream Armbian checkout is created locally as `armbian-build/` and is
ignored by Git.

```bash
git clone --depth=1 https://github.com/armbian/build armbian-build
cp -R patches/* armbian-build/
cd armbian-build

CPUTHREADS="$(nproc)" ./compile.sh build \
  BOARD=rk3528-h96max \
  BRANCH=vendor \
  BUILD_MINIMAL=yes \
  BUILD_DESKTOP=no \
  RELEASE=trixie \
  KERNEL_CONFIGURE=no \
  KERNEL_GIT=shallow
```

The finished image is written to `armbian-build/output/images/`.

## Writing to SD card

```bash

# Check location of SD card:
lsblk -o NAME,SIZE,MODEL,TRAN,MOUNTPOINTS

# Write the image to the SD card:
sudo dd \
  if=armbian-build/output/images/Armbian-unofficial_26.08.0-trunk_rk3528-h96max_trixie_vendor_6.1.115_minimal.img \
  of={SD card location} \
  bs=16M \
  oflag=direct \
  conv=fsync \
  status=progress

sync
```

## License

Licensed under [GPL-2.0](LICENSE).
