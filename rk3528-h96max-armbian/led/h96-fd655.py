#!/usr/bin/env python3
"""Experimental H96 Max FD655 clock, using the two GPIO wires from Android DT."""
import argparse
import datetime as dt
import json
import logging
from pathlib import Path
import time


DEFAULT = {
    "gpiochip": "/dev/gpiochip4", "clk": 19, "data": 20,
    "grid": [0, 4, 3, 2, 1],
    "icon_bits": {"colon": 4, "ethernet": 5, "wifi": 6},
    "brightness": 1, "delay_us": 20,
    "date_seconds": 15, "time_seconds": 45,
}
# Segment order from linux_openvfd's LED_decode_tab2.
SEG = (0x3f, 0x06, 0x5b, 0x4f, 0x66, 0x6d, 0x7d, 0x07, 0x7f, 0x6f)


def network_state(root=Path('/sys/class/net')):
    eth = wifi = False
    if not root.exists():
        return eth, wifi
    for iface in root.iterdir():
        if iface.name == 'lo':
            continue
        try:
            carrier = (iface / 'carrier').read_text().strip() == '1'
            oper = (iface / 'operstate').read_text().strip() == 'up'
            wireless = (iface / 'wireless').exists() or (iface / 'phy80211').exists()
        except OSError:
            continue
        if wireless:
            wifi |= carrier and oper
        elif (iface / 'device').exists():
            eth |= carrier and oper
    return eth, wifi


def frame(now, eth, wifi, config):
    icons = config['icon_bits']
    cycle = config['date_seconds'] + config['time_seconds']
    show_date = (now.hour * 3600 + now.minute * 60 + now.second) % cycle < config['date_seconds']
    mask = sum(1 << icons[key] for key, on in (
        ('colon', show_date or now.second % 2 == 0), ('ethernet', eth), ('wifi', wifi)) if on)
    first, second = (now.day, now.month) if show_date else (now.hour, now.minute)
    digits = (first // 10, first % 10, second // 10, second % 10)
    values = [mask, *(SEG[x] for x in digits)]
    output = [0] * 5
    for index, value in zip(config['grid'], values):
        output[index] = value
    return output


class FD655:
    def __init__(self, config):
        import gpiod
        from gpiod.line import Direction, Drive, Value
        self.Value = Value
        self.clk, self.data = config['clk'], config['data']
        self.delay = config['delay_us'] / 1_000_000
        settings = gpiod.LineSettings(direction=Direction.OUTPUT,
                                      drive=Drive.OPEN_DRAIN, output_value=Value.ACTIVE)
        self.lines = gpiod.request_lines(config['gpiochip'], consumer='h96-fd655',
                                         config={(self.clk, self.data): settings})
        self.set(self.clk, 1)
        self.set(self.data, 1)
        self.write(0x48, 0x01 | (min(config['brightness'], 2) << 5))

    def set(self, pin, high):
        self.lines.set_value(pin, self.Value.ACTIVE if high else self.Value.INACTIVE)

    def pause(self):
        time.sleep(self.delay)

    def byte(self, value):
        for bit in range(7, -1, -1):
            self.set(self.clk, 0)
            self.set(self.data, bool(value & (1 << bit)))
            self.pause()
            self.set(self.clk, 1)
            self.pause()
        self.set(self.clk, 0)
        self.set(self.data, 1)  # Release SDA for ACK; no clock stretching.
        self.pause()
        self.set(self.clk, 1)
        self.pause()
        self.set(self.clk, 0)

    def write(self, command, value):
        self.set(self.data, 0)
        self.pause()
        self.set(self.clk, 0)
        self.byte(command)
        self.byte(value)
        self.set(self.clk, 1)
        self.pause()
        self.set(self.data, 1)
        self.pause()

    def display(self, values):
        for grid, value in enumerate(values):
            self.write(0x66 + grid * 2, value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='/etc/h96-fd655.json')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    config = DEFAULT | (json.loads(Path(args.config).read_text()) if Path(args.config).exists() else {})
    if sorted(config['grid']) != list(range(5)) or any(not 0 <= x <= 7 for x in config['icon_bits'].values()):
        parser.error('invalid grid or icon bit mapping')
    if config['date_seconds'] <= 0 or config['time_seconds'] <= 0:
        parser.error('date_seconds and time_seconds must be positive')
    if args.dry_run:
        now = dt.datetime.now()
        print(json.dumps({'time': now.strftime('%H:%M:%S'),
                          'network': network_state(), 'frame': frame(now, *network_state(), config)}))
        return
    panel = FD655(config)
    previous = None
    while True:
        now = dt.datetime.now()
        current = frame(now, *network_state(), config)
        if current != previous:
            panel.display(current)
            previous = current
        time.sleep(0.5)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception:
        logging.exception('FD655 service stopped')
        raise
