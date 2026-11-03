#!/usr/bin/env python3
"""Install passive one-run diagnostics without changing driver or DTB."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

if os.geteuid() != 0:
    raise SystemExit('Run with sudo')
base = Path(__file__).resolve().parent
backup = Path('/var/backups/h96-wifi-boot-observe-20261102')
env = Path('/boot/armbianEnv.txt')
if backup.exists():
    raise SystemExit('Existing backup: inspect before repeating ' + str(backup))
trace = Path('/sys/kernel/tracing')
events = ['gpio:gpio_value', 'gpio:gpio_direction',
          'mmc:mmc_request_start', 'mmc:mmc_request_done',
          'power:clock_enable', 'power:clock_disable', 'power:clock_set_rate',
          'power:device_pm_callback_start', 'power:device_pm_callback_end',
          'regulator:regulator_enable', 'regulator:regulator_disable',
          'regulator:regulator_set_voltage', 'rpm:rpm_suspend', 'rpm:rpm_resume']
for event in events:
    if not (trace / 'events' / event.replace(':', '/') / 'enable').exists():
        raise SystemExit('Unavailable event: ' + event)
available = {line.split()[0] for line in (trace / 'available_filter_functions').read_text().splitlines()}
functions = ['dw_mci_set_ios', 'pinctrl_select_state', 'pinmux_enable_setting',
             'pinmux_disable_setting', 'rockchip_set_mux', 'rockchip_pmx_set']
if not all(function in available for function in functions):
    raise SystemExit('Required pinmux/MMC trace function absent')
functions += [name for name in ['tty_set_termios', 'uart_set_termios',
                               'serial8250_do_set_termios'] if name in available]
original = env.read_text()
if any(key in original for key in ['trace_event=', 'ftrace=', 'trace_buf_size=', 'ftrace_filter=']):
    raise SystemExit('Existing kernel tracing options: inspect before replacing')
backup.mkdir(mode=0o700)
shutil.copy2(env, backup / env.name)
share = Path('/usr/local/share')
share.mkdir(parents=True, exist_ok=True)
shutil.copy2(base / 'h96-wifi-trace-probes.txt', share / 'h96-wifi-trace-probes.txt')
for filename in ['h96-wifi-trace-arm.sh', 'h96-wifi-boot-observe.py']:
    target = Path('/usr/local/sbin') / filename
    if target.exists():
        raise SystemExit('Existing file: ' + str(target))
    shutil.copy2(base / filename, target)
    target.chmod(0o755)
for filename in ['h96-wifi-trace-arm.service', 'h96-wifi-boot-observe.service']:
    target = Path('/etc/systemd/system') / filename
    if target.exists():
        raise SystemExit('Existing unit: ' + str(target))
    shutil.copy2(base / filename, target)
    target.chmod(0o644)
subprocess.run(['systemd-analyze', 'verify',
                '/etc/systemd/system/h96-wifi-trace-arm.service',
                '/etc/systemd/system/h96-wifi-boot-observe.service'], check=True)
options = ('trace_buf_size=8192K trace_clock=global ftrace=function ftrace_filter=' +
           ','.join(functions) + ' trace_event=' + ','.join(events))
lines = original.splitlines()
found = False
for i, line in enumerate(lines):
    if line.startswith('extraargs='):
        lines[i] = line + ' ' + options
        found = True
if not found:
    lines.append('extraargs=' + options)
staged = '\n'.join(lines) + '\n'
env.write_text(staged)
(backup / 'manifest.json').write_text(json.dumps({
    'original_sha256': hashlib.sha256(original.encode()).hexdigest(),
    'staged_sha256': hashlib.sha256(staged.encode()).hexdigest(),
    'events': events, 'functions': functions,
}, indent=2))
subprocess.run(['systemctl', 'daemon-reload'], check=True)
subprocess.run(['systemctl', 'enable', 'h96-wifi-trace-arm.service',
                'h96-wifi-boot-observe.service'], check=True)
os.sync()
print('Installed for next boot; driver and DTB unchanged. Backup: ' + str(backup))
