#!/usr/bin/env python3
"""Passive trace drain and change snapshots. Never writes modem/GPIO registers."""
import glob
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time

TRACE = Path('/sys/kernel/tracing')
OUT = Path('/run/h96-wifi-boot-trace')
OUT.mkdir(parents=True, exist_ok=True)
stop = threading.Event()

def read(path):
    try:
        return Path(path).read_text(errors='replace')
    except (OSError, ValueError) as exc:
        return 'UNAVAILABLE: ' + str(exc)

def copy_trace():
    # Opening trace_pipe drains records already buffered since early kernel boot.
    import select
    fd = os.open(TRACE / 'trace_pipe', os.O_RDONLY | os.O_NONBLOCK)
    try:
        with (OUT / 'trace.txt').open('wb') as output:
            while not stop.is_set():
                if select.select([fd], [], [], 0.25)[0]:
                    try:
                        block = os.read(fd, 262144)
                    except BlockingIOError:
                        continue
                    if block:
                        output.write(block)
                        output.flush()
    finally:
        os.close(fd)

def paths():
    result = [
        '/sys/kernel/debug/gpio', '/sys/kernel/debug/mmc2/ios',
        '/sys/kernel/debug/clk/clk_summary',
        '/sys/kernel/debug/regulator/regulator_summary',
        '/proc/interrupts',
        '/proc/tty/driver/serial',
    ]
    patterns = [
        '/sys/kernel/debug/pinctrl/*/pinmux-pins',
        '/sys/kernel/debug/pinctrl/*/pinconf-pins',
        '/sys/kernel/debug/pinctrl/pinctrl-handles',
        '/sys/bus/platform/devices/ffc10000.mmc/power/*',
        '/sys/bus/sdio/devices/*/power/*',
        '/sys/bus/sdio/devices/*/uevent',
        '/sys/class/rfkill/rfkill*/{name,state,soft,hard}',
        '/sys/module/aic8800_*/parameters/*',
        '/sys/module/hci_uart/parameters/*',
        '/sys/class/bluetooth/hci*/uevent',
        '/sys/class/bluetooth/hci*/power/*',
        '/sys/bus/platform/devices/ffa00000.serial/power/*',
        '/sys/class/tty/ttyS*/device/power/*',
    ]
    # glob does not implement shell brace expansion.
    patterns.remove('/sys/class/rfkill/rfkill*/{name,state,soft,hard}')
    patterns.extend('/sys/class/rfkill/rfkill*/' + p for p in ['name', 'state', 'soft', 'hard'])
    for pattern in patterns:
        result.extend(glob.glob(pattern))
    return sorted(set(result))

reader = threading.Thread(target=copy_trace, daemon=True)
reader.start()
previous = {}
with (OUT / 'bluetooth-services.txt').open('w') as output:
    subprocess.run(['systemctl', 'cat', 'h96max-bluetooth.service', 'bluetooth.service'],
                   stdout=output, stderr=subprocess.STDOUT)
for filename in ['/etc/bluetooth/main.conf', '/etc/default/bluetooth']:
    (OUT / (Path(filename).name + '.txt')).write_text(read(filename))
started = time.monotonic()
(OUT / 'metadata.json').write_text(json.dumps({
    'boot_id': read('/proc/sys/kernel/random/boot_id').strip(),
    'cmdline': read('/proc/cmdline'),
    'sample_interval_seconds': 0.25,
    'duration_seconds_from_collector_start': 90,
    'trace_clock': read(TRACE / 'trace_clock'),
    'current_tracer': read(TRACE / 'current_tracer'),
}, indent=2))
try:
    with (OUT / 'changes.jsonl').open('w') as changes:
        while time.monotonic() - started < 90:
            stamp = time.clock_gettime(time.CLOCK_MONOTONIC)
            for path in paths():
                content = read(path)
                digest = hashlib.sha256(content.encode()).hexdigest()
                if previous.get(path) != digest:
                    changes.write(json.dumps({'monotonic': stamp, 'path': path,
                                              'content': content}) + '\n')
                    previous[path] = digest
            changes.flush()
            time.sleep(0.25)
finally:
    (TRACE / 'trace_marker').write_text('H96_COLLECTION_FINISHED\n')
    (TRACE / 'tracing_on').write_text('0\n')
    # Allow the reader to drain the last records before stopping it.
    time.sleep(0.5)
    stop.set()
    reader.join(timeout=2)
    for cpu in glob.glob(str(TRACE / 'per_cpu/cpu*')):
        (OUT / (Path(cpu).name + '-stats.txt')).write_text(read(Path(cpu) / 'stats'))
    for name in ['set_ftrace_filter', 'set_event', 'buffer_size_kb']:
        (OUT / (name + '.txt')).write_text(read(TRACE / name))
    with (OUT / 'kernel.txt').open('w') as output:
        subprocess.run(['dmesg', '--time-format=raw'], stdout=output, stderr=subprocess.STDOUT)
    with (OUT / 'device-tree.dts').open('w') as output:
        subprocess.run(['dtc', '-I', 'fs', '-O', 'dts', '/sys/firmware/devicetree/base'],
                       stdout=output, stderr=subprocess.DEVNULL)
    with (OUT / 'units.txt').open('w') as output:
        subprocess.run(['systemctl', 'show', 'h96-wifi-trace-arm.service',
                        'h96-wifi-boot-observe.service', 'systemd-modules-load.service',
                        '-p', 'Id', '-p', 'ActiveEnterTimestampMonotonic',
                        '-p', 'ExecMainStartTimestampMonotonic', '-p', 'Result'], stdout=output)
    with (OUT / 'bluetooth-journal.txt').open('w') as output:
        subprocess.run(['journalctl', '-b', '-o', 'short-monotonic', '--no-pager',
                        '-u', 'h96max-bluetooth.service', '-u', 'bluetooth.service',
                        '-u', 'systemd-rfkill.service', '-u', 'NetworkManager.service',
                        '-u', 'wpa_supplicant.service'], stdout=output)
    boot_id = read('/proc/sys/kernel/random/boot_id').strip()
    destination = Path('/var/log/h96-wifi-boot-trace') / boot_id
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(OUT, destination, dirs_exist_ok=True)
    # Remove our boot options only if no one edited the staged file meanwhile.
    backup = Path('/var/backups/h96-wifi-boot-observe-20261102')
    env = Path('/boot/armbianEnv.txt')
    manifest = json.loads((backup / 'manifest.json').read_text())
    if hashlib.sha256(env.read_bytes()).hexdigest() == manifest['staged_sha256']:
        shutil.copy2(backup / 'armbianEnv.txt', env)
        (destination / 'boot-options-restored.txt').write_text('Original armbianEnv.txt restored\n')
    else:
        (destination / 'boot-options-restored.txt').write_text('File edited; manual removal required\n')
    subprocess.run(['systemctl', 'disable', 'h96-wifi-trace-arm.service',
                    'h96-wifi-boot-observe.service'], check=False)
    os.sync()
    print('Saved Wi-Fi observation to ' + str(destination), flush=True)
