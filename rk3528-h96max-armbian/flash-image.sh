#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
DEFAULT_IMAGE="$SCRIPT_DIR/rk3528-h96max-armbian/armbian-build/output/images/Armbian-unofficial_26.11.0-trunk_Rk3528-h96max_trixie_vendor_6.1.172_minimal-rk3528-sd.img"

usage() {
  echo "Cách dùng: sudo $0 /dev/sdX [đường-dẫn-image.img.gz|.img]"
  echo "Image mặc định: $DEFAULT_IMAGE"
}

if [[ ${1:-} == -h || ${1:-} == --help ]]; then usage; exit 0; fi
if (( $# < 1 || $# > 2 )); then usage >&2; exit 2; fi
DEVICE=$1
IMAGE=${2:-$DEFAULT_IMAGE}

if (( EUID != 0 )); then echo 'Hãy chạy script bằng sudo.' >&2; exit 1; fi
if [[ ! -f $IMAGE || ! -r $IMAGE ]]; then echo "Không đọc được image: $IMAGE" >&2; exit 1; fi
if [[ ! -b $DEVICE || $(lsblk -dn -o TYPE -- "$DEVICE") != disk ]]; then
  echo "Thiết bị đích phải là toàn bộ ổ đĩa, ví dụ /dev/sda: $DEVICE" >&2; exit 1
fi
DEVICE=$(readlink -f -- "$DEVICE")

# Chỉ nhận ổ tháo rời hoặc ổ nối USB; tránh ghi nhầm ổ hệ thống.
RM=$(lsblk -dn -o RM -- "$DEVICE" | tr -d ' ')
TRAN=$(lsblk -dn -o TRAN -- "$DEVICE" | tr -d ' ')
if [[ $RM != 1 && $TRAN != usb ]]; then
  echo "Từ chối ghi lên ổ không tháo rời/không nối USB: $DEVICE" >&2; exit 1
fi

case $IMAGE in
  *.img.gz) FORMAT=gzip ;;
  *.img) FORMAT=raw ;;
  *) echo 'Image phải có đuôi .img hoặc .img.gz' >&2; exit 1 ;;
esac

echo "Image: $IMAGE"
echo "Ổ đích: $DEVICE"
lsblk -o NAME,PATH,SIZE,MODEL,TRAN,RM,TYPE,MOUNTPOINTS -- "$DEVICE"
echo "TOÀN BỘ DỮ LIỆU TRÊN $DEVICE SẼ BỊ XÓA."
read -r -p "Gõ chính xác $DEVICE để xác nhận: " CONFIRM
if [[ $CONFIRM != "$DEVICE" ]]; then echo 'Đã hủy.'; exit 1; fi

while IFS= read -r PART; do
  if findmnt -rn -S "$PART" >/dev/null; then
    echo "Tháo $PART"
    umount -- "$PART"
  fi
done < <(lsblk -ln -o PATH,TYPE -- "$DEVICE" | awk '$2 == "part" {print $1}')

echo 'Đang ghi image...'
if [[ $FORMAT == gzip ]]; then
  gzip -dc -- "$IMAGE" | dd of="$DEVICE" bs=4M iflag=fullblock oflag=direct status=progress conv=fsync
else
  dd if="$IMAGE" of="$DEVICE" bs=4M iflag=fullblock oflag=direct status=progress conv=fsync
fi
sync
blockdev --flushbufs "$DEVICE"

echo 'Đang đọc lại để xác minh...'
if [[ $FORMAT == gzip ]]; then
  # With a compressed image, stdin ends at the image boundary while the disk continues.
  # cmp reports that as EOF even when all image bytes match; use the decompressed size.
  IMAGE_SIZE=$(gzip -dc -- "$IMAGE" | wc -c)
  gzip -dc -- "$IMAGE" | cmp -n "$IMAGE_SIZE" - "$DEVICE"
else
  cmp -n "$(stat -c %s -- "$IMAGE")" "$IMAGE" "$DEVICE"
fi

echo "Hoàn tất: $DEVICE đã được flash và xác minh."
