#!/usr/bin/env python3
"""Install this H96 RK3528 SD system to identified eMMC; Android is erased."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import tempfile
import struct

STATE = Path('/var/lib/h96-emmc-install')
TARGET = '/dev/mmcblk1'
SOURCE = '/dev/mmcblk0'
MOUNT = Path('/mnt/h96-emmc-target')
RULE = Path('/etc/udev/rules.d/99-h96-emmc-detect.rules')
PAYLOADS = Path('/usr/lib/linux-u-boot-vendor-rk3528-h96max')
INSTALLATION_BLOCK_REASON = (
    'eMMC writes disabled: the installed loader crashes in SPL after DDR initialization. '
    'A bootable SD rootfs does not validate its loader. Establish recovery access '
    'and validate a replacement boot chain before enabling this installer.'
)
BOOT_SECTOR = 32768
BOOT_SECTORS = 1048576
ROOT_SECTOR = BOOT_SECTOR + BOOT_SECTORS
EXCLUDES = ['/dev/***', '/proc/***', '/sys/***', '/run/***', '/tmp/***',
            '/mnt/***', '/media/***', '/boot/***', '/lost+found',
            '/var/log/***', '/var/log.hdd/***', '/var/lib/h96-emmc-install/***']


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def output(*args):
    return subprocess.check_output(args, text=True).strip()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while data := f.read(4 * 1024 * 1024):
            h.update(data)
    return h.hexdigest()


def state(phase, **details):
    print(time.strftime('%Y-%m-%d %H:%M:%S'), phase, json.dumps(details), flush=True)
    STATE.mkdir(parents=True, exist_ok=True)
    temporary = STATE / 'state.json.tmp'
    temporary.write_text(json.dumps({'phase': phase, 'time': time.time(), **details}, indent=2) + '\n')
    temporary.replace(STATE / 'state.json')


def device_info():
    return json.loads(output('lsblk', '--tree', '-J', '-b', '-o',
                             'PATH,SIZE,TYPE,RO,MOUNTPOINTS', TARGET))['blockdevices'][0]


def all_unmounted(node):
    return not any(node.get('mountpoints') or []) and all(
        all_unmounted(child) for child in node.get('children', []))


def preflight(cid):
    require(os.geteuid() == 0, 'Run as root')
    for tool in ['sfdisk', 'partprobe', 'blockdev', 'mkfs.ext4', 'rsync',
                 'fdtget', 'mount', 'umount', 'e2fsck', 'blkid', 'udevadm']:
        require(shutil.which(tool), 'Missing tool: ' + tool)
    require('H96 Max RK3528' in Path('/proc/device-tree/model').read_text(), 'Unexpected board')
    require(output('findmnt', '-n', '-o', 'SOURCE', '/') == SOURCE + 'p2', 'Root is not expected SD')
    require(output('findmnt', '-n', '-o', 'SOURCE', '/boot') == SOURCE + 'p1', 'Boot is not expected SD')
    require(Path('/sys/block/mmcblk0/device/type').read_text().strip() == 'SD', 'Source is not SD')
    require(Path('/sys/block/mmcblk1/device/type').read_text().strip() == 'MMC', 'Target is not eMMC')
    require(Path('/sys/block/mmcblk1/device/name').read_text().strip() == 'CWBD3R', 'Unexpected eMMC')
    require(Path('/sys/block/mmcblk1/device/cid').read_text().strip() == cid, 'eMMC CID changed')
    info = device_info()
    require(info['size'] == 62537072640 and info['type'] == 'disk', 'Unexpected target size/type')
    require(all_unmounted(info), 'Target or a target partition is mounted')
    config = (PAYLOADS / 'u-boot-config-target-1').read_text()
    for option in ['CONFIG_CMD_MMC=y', 'CONFIG_CMD_EXT4=y', 'CONFIG_DISTRO_DEFAULTS=y',
                   'CONFIG_MMC_DW_ROCKCHIP=y', 'CONFIG_MMC_SDHCI_ROCKCHIP=y', 'CONFIG_ENV_IS_NOWHERE=y']:
        require(option in config, 'Missing bootloader capability: ' + option)
    fit = PAYLOADS / 'u-boot.itb'
    blob = fit.read_bytes()
    require(blob[:4] == bytes.fromhex('d00dfeed'), 'U-Boot payload is not FIT')
    total = struct.unpack('>I', blob[4:8])[0]
    offset = int(output('fdtget', '-t', 'x', str(fit), '/images/fdt', 'data-offset'), 16)
    length = int(output('fdtget', '-t', 'x', str(fit), '/images/fdt', 'data-size'), 16)
    embedded = None
    for alignment in [4, 512, 1024, 4096]:
        begin = (total + alignment - 1) // alignment * alignment + offset
        data = blob[begin:begin + length]
        if data[:4] == bytes.fromhex('d00dfeed') and len(data) == length:
            if struct.unpack('>I', data[4:8])[0] == length:
                embedded = data
                break
    require(embedded is not None, 'Cannot validate embedded bootloader DTB')
    with tempfile.TemporaryDirectory(prefix='h96-uboot-check-') as directory:
        dtb = Path(directory) / 'uboot.dtb'
        dtb.write_bytes(embedded)
        for node in ['/mmc@ffbf0000', '/mmc@ffc30000']:
            require(output('fdtget', str(dtb), node, 'status') == 'okay', 'U-Boot MMC controller disabled')
        require(output('fdtget', str(dtb), '/aliases', 'mmc0') == '/mmc@ffbf0000', 'Wrong U-Boot eMMC alias')
        require(output('fdtget', str(dtb), '/aliases', 'mmc1') == '/mmc@ffc30000', 'Wrong U-Boot SD alias')
    payloads = {}
    with open(SOURCE, 'rb', buffering=0) as sd:
        for name, sector in [('idbloader.img', 64), ('u-boot.itb', 16384)]:
            data = (PAYLOADS / name).read_bytes()
            require(data and sector * 512 + len(data) < BOOT_SECTOR * 512, 'Bootloader overlaps bootfs')
            sd.seek(sector * 512)
            require(sd.read(len(data)) == data, 'Payload differs from bootable SD: ' + name)
            payloads[name] = {'sector': sector, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    env = Path('/boot/armbianEnv.txt').read_text()
    relative = next(line.split('=', 1)[1] for line in env.splitlines() if line.startswith('fdtfile='))
    active = Path('/boot/dtb') / relative
    require(output('fdtget', str(active), '/mmc@ffbf0000', 'status') == 'okay', 'eMMC DTB is disabled')
    require(output('fdtget', str(active), '/mmc@ffc30000', 'max-frequency') == '25000000', 'Wrong SD settings')
    require(output('fdtget', str(active), '/mmc@ffc10000', 'max-frequency') == '50000000', 'Wrong Wi-Fi settings')
    require(output('blkid', '-s', 'UUID', '-o', 'value', SOURCE + 'p2') in env, 'SD root UUID mismatch')
    require(Path('/etc/systemd/system/armbian-led-state.service').readlink() == Path('/dev/null'),
            'GPIO38 workaround missing')
    require(not os.path.ismount(MOUNT), 'Install mountpoint is already in use')
    return {'source': SOURCE, 'target': TARGET, 'cid': cid, 'size': info['size'],
            'payloads': payloads, 'dtb': str(active), 'android_backup': 'explicitly waived by user'}


def rsync_root(checksum=False):
    command = ['rsync', '-aHAXx', '--numeric-ids', '--delete', '--info=progress2']
    if checksum:
        command.append('--checksum')
    for excluded in EXCLUDES:
        command += ['--exclude', excluded]
    result = subprocess.run(command + ['/', str(MOUNT) + '/'])
    # Files in the live source can disappear; the checksum pass must be clean.
    require(result.returncode == 0 or (result.returncode == 24 and not checksum),
            'Root copy failed: rsync exit ' + str(result.returncode))


def uuid(device):
    return output('blkid', '-p', '-s', 'UUID', '-o', 'value', device)


def configure(root_uuid, boot_uuid, before_env, active):
    final_name = 'rk3528-h96max-stock-rails-net-hdmi-emmc.dtb'
    final_dtb = MOUNT / 'boot/dtb/rockchip' / final_name
    shutil.copy2(active, final_dtb)
    lines = before_env.splitlines()
    values = {'rootdev': 'UUID=' + root_uuid, 'rootfstype': 'ext4',
              'fdtfile': 'rockchip/' + final_name, 'bootlogo': 'false'}
    seen = set()
    for i, line in enumerate(lines):
        key = line.split('=', 1)[0]
        if key in values:
            lines[i] = key + '=' + values[key]
            seen.add(key)
    lines += [key + '=' + value for key, value in values.items() if key not in seen]
    (MOUNT / 'boot/armbianEnv.txt').write_text('\n'.join(lines) + '\n')
    fstab = MOUNT / 'etc/fstab'
    changed = set()
    result = []
    for line in fstab.read_text().splitlines():
        fields = line.split()
        if fields and not line.lstrip().startswith('#') and len(fields) >= 2:
            if fields[1] in ['/', '/boot']:
                changed.add(fields[1])
                fields[0] = 'UUID=' + (root_uuid if fields[1] == '/' else boot_uuid)
                line = '\t'.join(fields)
        result.append(line)
    require(changed == {'/', '/boot'}, 'Expected root/boot entries missing from fstab')
    fstab.write_text('\n'.join(result) + '\n')
    (MOUNT / RULE.relative_to('/')).unlink(missing_ok=True)
    for folder in ['dev', 'proc', 'sys', 'run', 'tmp', 'mnt', 'media', 'boot', 'var/log', 'var/log.hdd']:
        (MOUNT / folder).mkdir(parents=True, exist_ok=True)
    (MOUNT / 'tmp').chmod(0o1777)
    (MOUNT / 'etc/h96-emmc-install.conf').write_text(
        f'SOURCE={SOURCE}\nTARGET={TARGET}\nROOT_UUID={root_uuid}\nBOOT_UUID={boot_uuid}\n'
        'ANDROID_BACKUP=waived_by_user\n')


def verify_payload(root_uuid, boot_uuid):
    require(uuid(TARGET + 'p1') == boot_uuid, 'Boot UUID changed')
    require(uuid(TARGET + 'p2') == root_uuid, 'Root UUID changed')
    require(uuid(SOURCE + 'p1') != boot_uuid and uuid(SOURCE + 'p2') != root_uuid, 'Duplicate SD/eMMC UUID')
    env = (MOUNT / 'boot/armbianEnv.txt').read_text()
    require('rootdev=UUID=' + root_uuid in env, 'Boot points to wrong root')
    fstab = (MOUNT / 'etc/fstab').read_text()
    require(root_uuid in fstab and boot_uuid in fstab, 'fstab mismatch')
    require(not (MOUNT / RULE.relative_to('/')).exists(), 'Detection-only read-only rule copied to target')
    require((MOUNT / 'etc/systemd/system/armbian-led-state.service').readlink() == Path('/dev/null'),
            'Target GPIO38 mask missing')
    for service in ['h96-fd655.service', 'h96max-bluetooth.service']:
        require((MOUNT / 'etc/systemd/system/multi-user.target.wants' / service).is_symlink(),
                'Target service not enabled: ' + service)
    firmware = Path('/lib/firmware/aic8800-gtx-a870f7f/SDIO/aic8800')
    for line in (firmware / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split()
        require(sha(MOUNT / firmware.relative_to('/') / name) == expected, 'Target firmware mismatch: ' + name)
    release = os.uname().release
    modules = Path('/lib/modules') / release
    radio_modules = list((modules / 'kernel/drivers/net/wireless/aicsemi/aic8800').rglob('*.ko*'))
    require(len(radio_modules) >= 3, 'Source radio module set incomplete')
    for original in radio_modules:
        require(sha(original) == sha(MOUNT / original.relative_to('/')), 'Target module mismatch: ' + str(original))
    for original in [Path('/boot') / ('vmlinuz-' + release), Path('/boot') / ('uInitrd-' + release)]:
        require(sha(original) == sha(MOUNT / original.relative_to('/')), 'Target kernel/initrd mismatch')
    require((MOUNT / 'lib/systemd/systemd').is_file(), 'Target init missing')
    relative = next(x.split('=', 1)[1] for x in env.splitlines() if x.startswith('fdtfile='))
    dtb = MOUNT / 'boot/dtb' / relative
    require(output('fdtget', str(dtb), '/mmc@ffbf0000', 'status') == 'okay', 'Target eMMC DT disabled')


def install(cid, resume=False):
    require(INSTALLATION_BLOCK_REASON is None, INSTALLATION_BLOCK_REASON)
    report = preflight(cid)
    STATE.mkdir(parents=True, exist_ok=True)
    manifest = STATE / 'preflight.json'
    if resume:
        previous = json.loads((STATE / 'state.json').read_text())
        require(previous.get('phase') == 'failed' and previous.get('error') ==
                'Kernel has not adopted new partition layout', 'Resume is only valid for the checked pre-format stop')
        table = json.loads(output('sfdisk', '-J', TARGET))['partitiontable']['partitions']
        require(len(table) == 2 and table[0]['start'] == BOOT_SECTOR and
                table[0]['size'] == BOOT_SECTORS and table[1]['start'] == ROOT_SECTOR,
                'Cannot resume: partition layout differs')
    else:
        require(not (STATE / 'write-started').exists(), 'A previous install started; inspect state instead of repeating')
    manifest.write_text(json.dumps(report, indent=2) + '\n')
    original_rule = RULE.read_bytes() if RULE.exists() else None
    before_env = Path('/boot/armbianEnv.txt').read_text()
    active = Path(report['dtb'])
    MOUNT.mkdir(parents=True, exist_ok=True)
    mounted = []
    try:
        # Suppress desktop auto-mounting while allowing this installation to write.
        RULE.write_text('ACTION=="add|change", SUBSYSTEM=="block", KERNEL=="mmcblk[0-9]*", '
                        'ATTRS{type}=="MMC", ENV{UDISKS_IGNORE}="1"\n')
        run('udevadm', 'control', '--reload-rules')
        require(all_unmounted(device_info()), 'eMMC mounted after preflight')
        for child in device_info().get('children', []):
            run('blockdev', '--flushbufs', child['path'])
        run('blockdev', '--flushbufs', TARGET)
        run('blockdev', '--setrw', TARGET)
        for child in device_info().get('children', []):
            if child['type'] == 'part':
                run('blockdev', '--setrw', child['path'])
        require(output('blockdev', '--getro', TARGET) == '0', 'Target remains read-only')
        (STATE / 'write-started').write_text(time.strftime('%Y-%m-%d %H:%M:%S') + '\n')
        state('partitioning', **report)
        sectors = report['size'] // 512
        root_sectors = ((sectors - 33 - ROOT_SECTOR) // 8) * 8
        layout = ('label: gpt\nunit: sectors\nfirst-lba: 2048\n\n'
                  f'start={BOOT_SECTOR}, size={BOOT_SECTORS}, type=BC13C2FF-59E6-4262-A352-B275FD6F7172, name="bootfs"\n'
                  f'start={ROOT_SECTOR}, size={root_sectors}, type=B921B045-1DF0-41C3-AF44-4C6F280D3FAE, name="rootfs"\n')
        if not resume:
            run('sfdisk', '--wipe', 'always', '--wipe-partitions', 'always', TARGET, input=layout, text=True)
        run('partprobe', TARGET)
        run('udevadm', 'settle')
        parts = [part for part in device_info().get('children', []) if part['type'] == 'part']
        require(len(parts) == 2 and parts[0]['path'] == TARGET + 'p1' and
                parts[0]['size'] == BOOT_SECTORS * 512 and parts[1]['path'] == TARGET + 'p2' and
                parts[1]['size'] == root_sectors * 512, 'Kernel has not adopted new partition layout')
        for part in parts:
            run('blockdev', '--setrw', part['path'])
        require(all_unmounted(device_info()), 'New target partition auto-mounted')
        state('formatting')
        # Classic ext4 boot features remain readable by the verified vendor U-Boot.
        run('mkfs.ext4', '-F', '-q', '-m', '0', '-L', 'armbi_emmc_boot', '-O',
            '^64bit,^metadata_csum,^metadata_csum_seed,^orphan_file', TARGET + 'p1')
        run('mkfs.ext4', '-F', '-q', '-m', '2', '-L', 'armbi_emmc_root', '-O', '^orphan_file', TARGET + 'p2')
        root_uuid, boot_uuid = uuid(TARGET + 'p2'), uuid(TARGET + 'p1')
        require(root_uuid != uuid(SOURCE + 'p2') and boot_uuid != uuid(SOURCE + 'p1'), 'UUID collision')
        run('mount', TARGET + 'p2', str(MOUNT)); mounted.append(MOUNT)
        (MOUNT / 'boot').mkdir(exist_ok=True)
        run('mount', TARGET + 'p1', str(MOUNT / 'boot')); mounted.append(MOUNT / 'boot')
        state('copying-root', root_uuid=root_uuid, boot_uuid=boot_uuid)
        rsync_root()
        state('checksum-pass')
        rsync_root(checksum=True)
        state('copying-boot')
        run('rsync', '-aHAX', '--numeric-ids', '--delete', '/boot/', str(MOUNT / 'boot') + '/')
        configure(root_uuid, boot_uuid, before_env, active)
        state('verifying-files')
        verify_payload(root_uuid, boot_uuid)
        os.sync()
        for mount in reversed(mounted):
            run('umount', str(mount))
        mounted.clear()
        state('checking-filesystems')
        run('e2fsck', '-f', '-n', TARGET + 'p1')
        run('e2fsck', '-f', '-n', TARGET + 'p2')
        # Erase only the unallocated loader gap, preserving primary GPT at LBAs 0..33.
        state('writing-verified-bootloader')
        run('dd', 'if=/dev/zero', 'of=' + TARGET, 'bs=512', 'seek=34',
            'count=' + str(BOOT_SECTOR - 34), 'conv=notrunc,fsync', 'status=none')
        for name, details in report['payloads'].items():
            run('dd', 'if=' + str(PAYLOADS / name), 'of=' + TARGET,
                'bs=512', 'seek=' + str(details['sector']), 'conv=notrunc,fsync', 'status=none')
        for partition in [TARGET + 'p1', TARGET + 'p2', TARGET]:
            run('blockdev', '--flushbufs', partition)
        with open(TARGET, 'rb', buffering=0) as disk:
            for name, details in report['payloads'].items():
                disk.seek(details['sector'] * 512)
                require(hashlib.sha256(disk.read(details['size'])).hexdigest() == details['sha256'],
                        'Bootloader read-back mismatch: ' + name)
        # Read filesystem identity again after whole-device loader writes/cache flushes.
        require(uuid(TARGET + 'p1') == boot_uuid and uuid(TARGET + 'p2') == root_uuid,
                'Filesystem metadata changed after bootloader write')
        run('sfdisk', '--verify', TARGET)
        run('mount', '-o', 'ro,noload', TARGET + 'p2', str(MOUNT)); mounted.append(MOUNT)
        run('mount', '-o', 'ro,noload', TARGET + 'p1', str(MOUNT / 'boot')); mounted.append(MOUNT / 'boot')
        verify_payload(root_uuid, boot_uuid)
        for mount in reversed(mounted):run('umount', str(mount))
        mounted.clear()
        require(output('findmnt', '-n', '-o', 'SOURCE', '/') == SOURCE + 'p2', 'Source root changed')
        require(Path('/boot/armbianEnv.txt').read_text() == before_env, 'SD boot configuration changed')
        state('complete-awaiting-no-sd-boot', root_uuid=root_uuid, boot_uuid=boot_uuid,
              source=SOURCE, target=TARGET, cid=cid, size=report['size'], android_backup='waived_by_user')
    except BaseException as error:
        state('failed', error=str(error))
        raise
    finally:
        for mount in reversed(mounted):
            subprocess.run(['umount', str(mount)])
        if original_rule is not None:
            RULE.write_bytes(original_rule)
        else:
            RULE.unlink(missing_ok=True)
        subprocess.run(['udevadm', 'control', '--reload-rules'])
        if not any(os.path.ismount(path) for path in [MOUNT, MOUNT / 'boot']):
            subprocess.run(['blockdev', '--flushbufs', TARGET])
            subprocess.run(['blockdev', '--setro', TARGET])
        os.sync()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expect-cid', required=True)
    parser.add_argument('--erase-android', action='store_true')
    parser.add_argument('--no-android-backup', action='store_true')
    parser.add_argument('--resume-after-partitioning', action='store_true')
    args = parser.parse_args()
    require(re.fullmatch('[0-9a-fA-F]{32}', args.expect_cid), 'Expected a complete eMMC CID')
    if not (args.erase_android and args.no_android_backup):
        print(json.dumps(preflight(args.expect_cid), indent=2))
        print('PREFLIGHT ONLY: installation requires explicit --erase-android --no-android-backup')
        return
    install(args.expect_cid, resume=args.resume_after_partitioning)


if __name__ == '__main__':
    main()
