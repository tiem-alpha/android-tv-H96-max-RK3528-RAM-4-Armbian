#!/usr/bin/env python3
"""Skip LED restore at next boot and repeat the same passive Wi-Fi/BT trace."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

if os.geteuid() != 0:
    raise SystemExit('Run with sudo')
env = Path('/boot/armbianEnv.txt')
trace_backup = Path('/var/backups/h96-wifi-boot-observe-20261102')
backup = Path('/var/backups/h96-no-led-restore-20261102')
manifest = json.loads((trace_backup / 'manifest.json').read_text())
original = env.read_text()
if hashlib.sha256(original.encode()).hexdigest() != manifest['original_sha256']:
    raise SystemExit('Boot configuration changed since previous trace; inspect first')
if backup.exists():
    raise SystemExit('Backup already exists; do not repeat blindly')
backup.mkdir(mode=0o700)
shutil.copy2(env, backup / env.name)
shutil.copy2('/etc/armbian-leds.conf', backup / 'armbian-leds.conf')
state = subprocess.run(['systemctl', 'is-enabled', 'armbian-led-state.service'],
                       text=True, capture_output=True)
(backup / 'led-service-before.txt').write_text(state.stdout + state.stderr)
options = ('trace_buf_size=8192K trace_clock=global ftrace=function ftrace_filter=' +
           ','.join(manifest['functions']) + ' trace_event=' + ','.join(manifest['events']))
lines = original.splitlines()
for i, line in enumerate(lines):
    if line.startswith('extraargs='):
        lines[i] = line + ' ' + options
        break
else:
    raise SystemExit('No extraargs in boot configuration')
staged = '\n'.join(lines) + '\n'
if hashlib.sha256(staged.encode()).hexdigest() != manifest['staged_sha256']:
    raise SystemExit('Reconstructed trace config differs from previous trial')
try:
    # No --now: do not stop the active service or change GPIOs in this session.
    subprocess.run(['systemctl', 'mask', 'armbian-led-state.service'], check=True)
    env.write_text(staged)
    subprocess.run(['systemctl', 'enable', 'h96-wifi-trace-arm.service',
                    'h96-wifi-boot-observe.service'], check=True)
    os.sync()
except Exception:
    env.write_text(original)
    subprocess.run(['systemctl', 'unmask', 'armbian-led-state.service'])
    subprocess.run(['systemctl', 'disable', 'h96-wifi-trace-arm.service',
                    'h96-wifi-boot-observe.service'])
    os.sync()
    raise
print('LED restore masked for next boot; same Wi-Fi/BT trace rearmed.')
print('Driver, firmware and current GPIO state were not changed.')
print('After capture, trace options/services revert; LED restore remains masked for evaluation.')
print('To restore LED service later: sudo systemctl unmask armbian-led-state.service')
