#!/usr/bin/env python3
"""Capture H96 Max RK3528 UART output until Ctrl+C."""

import argparse
from datetime import datetime
from pathlib import Path
import sys

import serial
from serial.tools import list_ports


def find_port():
    ports = list(list_ports.comports())
    cp210x = [p.device for p in ports if p.vid == 0x10C4 and p.pid == 0xEA60]
    if len(cp210x) == 1:
        return cp210x[0]
    if len(ports) == 1:
        return ports[0].device
    choices = ", ".join(p.device for p in ports) or "none"
    raise SystemExit(f"Cannot choose a serial port automatically ({choices}); pass --port")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="serial device; defaults to the connected CP2102")
    parser.add_argument("--baud", type=int, default=115_200)
    parser.add_argument("--output", type=Path, help="text log path")
    args = parser.parse_args()
    port_name = args.port or find_port()
    selected = next((p for p in list_ports.comports() if p.device == port_name), None)
    if (selected and selected.vid == 0x10C4 and selected.pid == 0xEA60
            and "CP2102N" not in (selected.product or "")
            and "CP2102" in (selected.product or "") and args.baud > 1_000_000):
        parser.error(
            f"{port_name} is a CP2102, which cannot reliably receive {args.baud} baud. "
            "Use a USB-UART adapter rated for at least 1.5 Mbaud (for example CP2102N or FT232H)."
        )
    output = args.output or Path(f"uart-rk3528-{datetime.now():%Y%m%d-%H%M%S}.log")
    output.parent.mkdir(parents=True, exist_ok=True)
    raw_output = output.with_name(output.name + ".raw")

    try:
        with serial.Serial(port_name, args.baud, timeout=0.5) as port, \
                output.open("w", encoding="utf-8") as text_log, \
                raw_output.open("wb") as raw_log:
            print(f"Reading {port.name} at {args.baud} 8N1. Power-cycle the box; press Ctrl+C to stop.")
            print(f"Text: {output}\nRaw:  {raw_output}")
            while True:
                data = port.read(4096)
                if data:
                    raw_log.write(data)
                    raw_log.flush()
                    decoded = data.decode("utf-8", errors="replace")
                    text_log.write(decoded)
                    text_log.flush()
                    sys.stdout.write(decoded)
                    sys.stdout.flush()
    except KeyboardInterrupt:
        print(f"\nSaved {output} and {raw_output}")
    except serial.SerialException as exc:
        raise SystemExit(f"Serial error: {exc}") from exc


if __name__ == "__main__":
    main()
