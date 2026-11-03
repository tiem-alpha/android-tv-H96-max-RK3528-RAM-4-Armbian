#!/usr/bin/env bash
# Verify and stage the bundled firmware; no network or Git checkout required.
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "${repo_dir}/patches/config/h96-aic8800.conf"
manifest="${repo_dir}/patches/config/h96-aic8800-firmware.sha256"
source_dir="${repo_dir}/patches/vendor/aic8800"
(cd "$source_dir/firmware" && sha256sum -c "$manifest")
destination="${repo_dir}/patches/userpatches/overlay${H96_AIC_FW_DIR}"
mkdir -p "$destination"
while read -r checksum file; do
    install -m 0644 "$source_dir/firmware/$file" "$destination/$file"
done < "$manifest"
install -m 0644 "$manifest" "$destination/SHA256SUMS"
install -m 0644 "${repo_dir}/patches/config/h96-aic8800.conf" \
    "${repo_dir}/patches/userpatches/overlay/h96-radio.conf"
(cd "$destination" && sha256sum -c SHA256SUMS)
echo "Prepared pinned GTX firmware: $destination"
