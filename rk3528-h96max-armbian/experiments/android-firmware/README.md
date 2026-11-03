# Archived Android firmware extraction

`capture-aic-firmware.py` is the earlier ADB-based factory firmware extractor. The current image uses the complete matching GTX firmware set in `patches/vendor/aic8800/firmware` and does not call this tool. Android binaries remain historical comparison material.

The extractor was moved two directory levels below the repository root. It still writes the old, ignored Android firmware overlay when explicitly run from a host with a connected Android box; it does not replace the GTX firmware used by the current build.
