#!/usr/bin/env bash
# Fetch and verify the complete firmware set from the pinned driver repository.
set -euo pipefail
repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "${repo_dir}/patches/config/h96-aic8800.conf"
manifest="${repo_dir}/patches/config/h96-aic8800-firmware.sha256"
source_dir=${H96_AIC_SOURCE_DIR:-${repo_dir}/armbian-build/cache/h96-aic8800-gtx/${H96_AIC_COMMIT}}
if [[ -z ${H96_AIC_SOURCE_DIR:-} ]]; then
    mkdir -p "$source_dir"
    if [[ ! -d "$source_dir/.git" ]]; then
        git init -q "$source_dir"
        git -C "$source_dir" remote add origin "$H96_AIC_REPO"
    fi
    if ! git -C "$source_dir" cat-file -e "${H96_AIC_COMMIT}^{commit}" 2>/dev/null; then
        git -C "$source_dir" fetch --depth=1 origin "$H96_AIC_COMMIT"
    fi
    git -C "$source_dir" checkout --detach "$H96_AIC_COMMIT"
fi
[[ $(git -C "$source_dir" rev-parse HEAD) == "$H96_AIC_COMMIT" ]] || {
    echo 'AIC source does not match the pinned commit' >&2; exit 1;
}
git -C "$source_dir" diff --quiet HEAD -- "$H96_AIC_DRIVER_SUBDIR" "$H96_AIC_FIRMWARE_SUBDIR" || {
    echo 'AIC source/firmware checkout has modifications' >&2; exit 1;
}
(cd "$source_dir/$H96_AIC_FIRMWARE_SUBDIR" && sha256sum -c "$manifest")
destination="${repo_dir}/patches/userpatches/overlay${H96_AIC_FW_DIR}"
mkdir -p "$destination"
while read -r checksum file; do
    install -m 0644 "$source_dir/$H96_AIC_FIRMWARE_SUBDIR/$file" "$destination/$file"
done < "$manifest"
install -m 0644 "$manifest" "$destination/SHA256SUMS"
install -m 0644 "${repo_dir}/patches/config/h96-aic8800.conf" \
    "${repo_dir}/patches/userpatches/overlay/h96-radio.conf"
(cd "$destination" && sha256sum -c SHA256SUMS)
echo "Prepared pinned GTX firmware: $destination"
