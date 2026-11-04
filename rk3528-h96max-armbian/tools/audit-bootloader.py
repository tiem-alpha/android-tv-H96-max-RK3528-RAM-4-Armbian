#!/usr/bin/env python3
"""Read-only SPL ELF, embedded DTB and external-data FIT consistency audit."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess


def command(*args):
    return subprocess.check_output([str(arg) for arg in args], text=True).strip()


class Elf:
    """Minimal ELF64 little-endian section reader; no third-party modules."""

    def __init__(self, path):
        self.path = path
        self.blob = path.read_bytes()
        if self.blob[:6] != b'\x7fELF\x02\x01':
            raise ValueError('Expected little-endian ELF64')
        offset = struct.unpack_from('<Q', self.blob, 40)[0]
        size, count = struct.unpack_from('<HH', self.blob, 58)
        self.sections = [struct.unpack_from('<IIQQQQIIQQ', self.blob, offset + i * size)
                         for i in range(count)]
        self.symbols = {}
        for line in command('aarch64-linux-gnu-nm', '-S', '--defined-only', path).splitlines():
            fields = line.split()
            if len(fields) == 4:
                address, length, kind, name = fields
                self.symbols[name] = (int(address, 16), int(length, 16))

    def read(self, address, size):
        for _, kind, flags, base, offset, length, *_ in self.sections:
            if flags & 2 and kind != 8 and base <= address and address + size <= base + length:
                return self.blob[offset + address - base:offset + address - base + size]
        raise ValueError(f'Address outside file-backed allocated sections: {address:#x}+{size:#x}')

    def pointer(self, address):
        return struct.unpack('<Q', self.read(address, 8))[0]

    def string(self, address):
        data = bytearray()
        for i in range(256):
            char = self.read(address + i, 1)[0]
            if not char:
                return data.decode('ascii')
            data.append(char)
        raise ValueError(f'Unterminated string at {address:#x}')


def get(fdt, node, prop, kind='s'):
    return command('fdtget', '-t', kind, fdt, node, prop)


def driver_audit(elf):
    result = []
    for name, (address, size) in elf.symbols.items():
        if not name.startswith('_u_boot_list_2_driver_2_'):
            continue
        # This retained vendor AArch64 ABI places of_match at offset 16.
        if size != 120:
            raise ValueError(f'Unsupported driver ABI: {name}, size {size}')
        table = elf.pointer(address + 16)
        matches = []
        if table:
            for i in range(256):
                pointer = elf.pointer(table + i * 16)
                if not pointer:
                    break
                matches.append({'pointer': hex(pointer), 'compatible': elf.string(pointer)})
            else:
                raise ValueError(f'Unterminated compatible table: {name}')
        result.append({'driver': name.removeprefix('_u_boot_list_2_driver_2_'),
                       'address': hex(address), 'table': hex(table), 'matches': matches})
    if not result:
        raise ValueError('No driver linker-list symbols found')
    return result


def fit_audit(path):
    blob = path.read_bytes()
    if blob[:4] != bytes.fromhex('d00dfeed'):
        raise ValueError('FIT magic missing')
    total = struct.unpack_from('>I', blob, 4)[0]
    # Vendor include/image.h uses FIT_ALIGN(size) = ALIGN(size, 512).
    external_base = (total + 511) & ~511
    images = []
    ranges = []
    for name in command('fdtget', '-l', path, '/images').split():
        node = '/images/' + name
        props = command('fdtget', '-p', path, node).split()
        size = int(get(path, node, 'data-size', 'x'), 16)
        start = (int(get(path, node, 'data-position', 'x'), 16)
                 if 'data-position' in props else
                 external_base + int(get(path, node, 'data-offset', 'x'), 16))
        data = blob[start:start + size]
        if len(data) != size:
            raise ValueError(f'Truncated FIT payload {name}')
        hashes = []
        for child in command('fdtget', '-l', path, node).split():
            if not child.startswith('hash'):
                continue
            algo = get(path, node + '/' + child, 'algo')
            expected = bytes(int(x, 16) for x in get(path, node + '/' + child, 'value', 'bx').split()).hex()
            actual = hashlib.new(algo, data).hexdigest()
            if expected != actual:
                raise ValueError(f'FIT hash mismatch: {name}/{child}')
            hashes.append({'algorithm': algo, 'value': actual, 'verified': True})
        if not hashes:
            raise ValueError(f'No verified FIT hash: {name}')
        image = {'name': name, 'file_offset': start, 'size': size, 'hashes': hashes}
        if 'load' in props:
            cells = get(path, node, 'load', 'x').split()
            address = 0
            for cell in cells:
                address = (address << 32) | int(cell, 16)
            image['load_start'] = hex(address)
            image['load_end'] = hex(address + size)
            ranges.append((address, address + size, name))
        images.append(image)
    for i, (start, end, name) in enumerate(ranges):
        for other_start, other_end, other in ranges[i + 1:]:
            if max(start, other_start) < min(end, other_end):
                raise ValueError(f'FIT load ranges overlap: {name}, {other}')
    config = get(path, '/configurations', 'default')
    node = '/configurations/' + config
    references = {}
    available = {image['name'] for image in images}
    for key in ('firmware', 'loadables', 'fdt'):
        refs = get(path, node, key).split()
        if not set(refs) <= available:
            raise ValueError(f'FIT configuration has missing {key}')
        references[key] = refs
    return {'sha256': hashlib.sha256(blob).hexdigest(), 'size': len(blob),
            'configuration': config, 'references': references, 'images': images,
            'load_ranges_disjoint': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uboot-tree', type=Path, required=True)
    args = parser.parse_args()
    tree = args.uboot_tree.resolve()
    elf = Elf(tree / 'spl/u-boot-spl')
    spl = (tree / 'spl/u-boot-spl.bin').read_bytes()
    dts = []
    for relative in ('spl/u-boot-spl.dtb', 'u-boot.dtb'):
        path = tree / relative
        dts.append({'file': relative, 'model': get(path, '/', 'model'),
                    'compatible': get(path, '/', 'compatible'),
                    'stdout': get(path, '/chosen', 'stdout-path'),
                    'sd_max_hz': int(get(path, '/mmc@ffc30000', 'max-frequency', 'u')),
                    'emmc_max_hz': int(get(path, '/mmc@ffbf0000', 'max-frequency', 'u'))})
    result = {'status': 'STATIC_CHECKS_PASS_RUNTIME_NOT_TESTED',
              'tree': str(tree), 'spl': {'sha256': hashlib.sha256(spl).hexdigest(),
                                       'size': len(spl), 'drivers': driver_audit(elf)},
              'uboot': {'drivers': driver_audit(Elf(tree / 'u-boot'))},
              'embedded_dtb': dts, 'fit': fit_audit(tree / 'u-boot.itb')}
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
