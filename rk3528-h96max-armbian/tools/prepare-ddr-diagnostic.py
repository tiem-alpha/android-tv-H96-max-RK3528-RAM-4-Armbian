#!/usr/bin/env python3
"""Prepare an unvalidated DDR3 528 MHz diagnostic loader. Never write devices."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

BASELINE_SHA = '33141f9180217ab259c79fafcab09f2ed65c4e10bba5685f6f7d9bfc56fe68be'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def params(path):
    return dict(line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uboot-tree', type=Path, required=True)
    parser.add_argument('--ddr', type=Path, required=True)
    parser.add_argument('--ddrbin-tool', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error('Output directory must not exist; keep previous evidence intact')
    tree = args.uboot_tree.resolve()
    tool = args.ddrbin_tool.resolve()
    original = args.ddr.read_bytes()
    spl = (tree / 'spl/u-boot-spl.bin').read_bytes()
    mkimage = tree / 'tools/mkimage'
    with tempfile.TemporaryDirectory(prefix='h96-ddr-') as directory:
        work = Path(directory)

        def run(*command):
            result = subprocess.run([str(value) for value in command], cwd=work,
                                    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            with (work / 'build.log').open('a') as log:
                log.write(result.stdout)
            if result.returncode:
                raise RuntimeError(result.stdout[-2000:])

        def pack(name):
            run(mkimage, '-n', 'rk3528', '-T', 'rksd', '-d', 'ddr.bin:spl.bin', name)

        (work / 'ddr.bin').write_bytes(original)
        (work / 'spl.bin').write_bytes(spl)
        pack('baseline.img')
        baseline = (work / 'baseline.img').read_bytes()
        if digest(baseline) != BASELINE_SHA:
            raise RuntimeError('Inputs do not reproduce the audited incident loader')
        run(tool, 'rk3528', '-g', 'before.txt', 'ddr.bin')
        before = params(work / 'before.txt')
        if before.get('ddr3_freq') != '1056':
            raise RuntimeError('Unexpected baseline DDR3 frequency')
        changes = ['start tag=0x12345678']
        changes += [key + '=' + ('528' if key == 'ddr3_freq' else '')
                    for key in before if key != 'start tag']
        (work / 'change.txt').write_text('\n'.join(changes) + '\nend\n')
        run(tool, 'rk3528', 'change.txt', 'ddr.bin')
        run(tool, 'rk3528', '-g', 'after.txt', 'ddr.bin')
        after = params(work / 'after.txt')
        expected = dict(before, ddr3_freq='528')
        if after != expected:
            raise RuntimeError('DDR tool changed unexpected parameters')
        pack('idbloader-ddr3-528-diagnostic.img')
        candidate = (work / 'idbloader-ddr3-528-diagnostic.img').read_bytes()
        if len(candidate) != len(baseline) or candidate.find(spl) != baseline.find(spl):
            raise RuntimeError('SPL changed or loader layout changed')
        if digest(original) != digest(args.ddr.read_bytes()):
            raise RuntimeError('Source DDR blob changed')
        metadata = {
            'status': 'UNVALIDATED_DIAGNOSTIC_DO_NOT_AUTOFLASH',
            'purpose': 'Test DDR instability separately; not a confirmed SPL repair',
            'change': {'ddr3_freq_mhz': [1056, 528]},
            'baseline_sha256': digest(baseline),
            'candidate_sha256': digest(candidate),
            'spl_sha256': digest(spl),
            'ddr_original_sha256': digest(original),
            'ddr_candidate_sha256': digest((work / 'ddr.bin').read_bytes()),
            'ddrbin_tool_sha256': digest(tool.read_bytes()),
            'spl_offset': candidate.find(spl),
            'hardware_validation': 'pending; recovery access required',
        }
        (work / 'manifest.json').write_text(json.dumps(metadata, indent=2) + '\n')
        output.mkdir(parents=True)
        for name in ['idbloader-ddr3-528-diagnostic.img', 'ddr.bin', 'before.txt',
                     'after.txt', 'change.txt', 'manifest.json', 'build.log']:
            shutil.copy2(work / name, output / name)
    print(output / 'manifest.json')


if __name__ == '__main__':
    main()
