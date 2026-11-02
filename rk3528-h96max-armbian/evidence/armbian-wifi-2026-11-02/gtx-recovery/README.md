# Offline recovery after GTX boot hang

User reported no boot/network after matched GTX firmware deployment. SD /dev/sda2 was mounted at /media/nguyentiem/armbi_root. Saved latest journal kernel log and archived console-ramoops log here. Latest journal contains no Oops, NULL dereference, or stack trace; it ends near NetworkManager/Bluetooth initialization. Archived pstore console is from an earlier long-running boot and does not establish the current failure cause.

The GTX source aicbsp_get_feature dereferences global aicbsp_sdiodev without a NULL check. This is a real candidate defect, but no evidence yet ties it to this boot hang. Do not treat the restored card as a validated fixed GTX port.

Verified SHA256SUMS of /var/backups/h96-wifi-gtx-20261102 and restored both modules from that pre-GTX backup. Restored BSP SHA-256 acff7a3ad446aaf69788d0d7327dcd79164bd39a0152b12c3c9963ea90ad8d21, FDRV 7afc97f3d509e022e9dc3bf073e6877ba82a7d5cbab8434b52b6191e4e9bf9c9. This is the previously bootable 50 MHz/power-control-disabled pair selecting preserved Android firmware. Ran depmod -b on mounted root and sync. Failed GTX pair and kernel log saved on card in /var/backups/h96-wifi-gtx-failed-20261102. DTB and eMMC not modified. Runtime recovery awaits user reinserting SD and powering up.
