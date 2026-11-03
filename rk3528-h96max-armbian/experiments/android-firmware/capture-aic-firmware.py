#!/usr/bin/env python3
"""Copy this box's AIC8800 firmware into the Armbian image overlay."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[2]
target = root / "patches/userpatches/overlay/lib/firmware/aic8800/SDIO/aic8800D80"
names = [
    "/vendor/etc/firmware/" + name
    for name in subprocess.check_output(
        ["adb", "shell", "su", "0", "ls", "-1", "/vendor/etc/firmware"],
        text=True,
    ).splitlines()
    if name.startswith(("aic_userconfig", "fmacfw", "fw_adid", "fw_patch", "lmacfw"))
]
if not names:
    raise SystemExit("No AIC8800 firmware found on the connected Android box")
target.mkdir(parents=True, exist_ok=True)
for name in names:
    with (target / Path(name).name).open("wb") as output:
        subprocess.run(["adb", "exec-out", "su", "0", "cat", name],
                       check=True, stdout=output)
print(f"Copied {len(names)} firmware files to {target}")
