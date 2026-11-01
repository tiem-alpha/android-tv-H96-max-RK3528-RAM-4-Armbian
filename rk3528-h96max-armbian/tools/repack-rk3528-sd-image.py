#!/usr/bin/env python3
"""Install the RK3528 multitool-style boot payloads into an Armbian SD image."""

import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

SECTOR_SIZE = 512
PAYLOADS = (("idbloader.img", 0x40), ("u-boot.itb", 0x4000))
FIRST_PARTITION_SECTOR = 0x8000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="existing Armbian .img")
    parser.add_argument("uboot_deb", type=Path, help="matching linux-u-boot .deb")
    parser.add_argument("output", type=Path, help="new SD .img")
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error("output must differ from source")
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")
    for path in (args.source, args.uboot_deb):
        if not path.is_file():
            parser.error(f"missing file: {path}")

    with tempfile.TemporaryDirectory(prefix="rk3528-boot-") as temporary:
        subprocess.run(["dpkg-deb", "-x", str(args.uboot_deb), temporary], check=True)
        payload_dir = Path(temporary) / "usr/lib/linux-u-boot-vendor-rk3528-h96max"
        payloads = []
        for name, sector in PAYLOADS:
            data = (payload_dir / name).read_bytes()
            if sector * SECTOR_SIZE + len(data) > FIRST_PARTITION_SECTOR * SECTOR_SIZE:
                parser.error(f"{name} overlaps the first partition")
            payloads.append((name, sector, data))

        with args.source.open("rb") as source:
            source.seek(SECTOR_SIZE)
            if source.read(8) != b"EFI PART":
                parser.error("source does not have a GPT header")
            source.seek(0)
            # First GPT entry: start LBA follows two 16-byte GUIDs.
            source.seek(2 * SECTOR_SIZE + 32)
            first_start = int.from_bytes(source.read(8), "little")
            if first_start < FIRST_PARTITION_SECTOR:
                parser.error(f"first partition starts too early: sector {first_start}")

        args.output.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(["cp", "--reflink=auto", "--sparse=always", "--", str(args.source), str(args.output)], check=True)
            with args.output.open("r+b") as image:
                for name, sector, data in payloads:
                    image.seek(sector * SECTOR_SIZE)
                    image.write(data)
                    print(f"wrote {name}: sector {sector:#x}, {len(data)} bytes")
                image.flush()
                for name, sector, data in payloads:
                    image.seek(sector * SECTOR_SIZE)
                    if image.read(len(data)) != data:
                        raise RuntimeError(f"verification failed: {name}")
            digest = hashlib.sha256()
            with args.output.open("rb") as image:
                for chunk in iter(lambda: image.read(8 * 1024 * 1024), b""):
                    digest.update(chunk)
            checksum = args.output.with_name(args.output.name + ".sha256")
            checksum.write_text(f"{digest.hexdigest()}  {args.output.name}\n")
            print(f"verified {args.output}")
            print(f"SHA-256: {digest.hexdigest()}")
        except BaseException:
            args.output.unlink(missing_ok=True)
            raise


if __name__ == "__main__":
    main()
