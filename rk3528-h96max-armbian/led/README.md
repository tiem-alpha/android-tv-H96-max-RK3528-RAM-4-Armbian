# H96 Max FD655 front-panel display

The Android driver log identifies GPIO4 line 20 as CLK and line 19 as DAT. This service drives the two-wire FD655 interface using the protocol documented by `evidence/linux_openvfd`.

Each 60-second cycle displays `DD/MM` for 15 seconds with a steady separator, then `HH:MM` for 45 seconds with a blinking colon. Ethernet and Wi-Fi icons are enabled when the corresponding interface has carrier and `operstate=up`. Change `date_seconds` and `time_seconds` in `/etc/h96-fd655.json` to adjust the cycle. The display follows the system's local time; check the timezone and time synchronization after boot.

The current image build installs the program, JSON configuration, `python3-libgpiod` and enabled systemd service. For a manual installation on a compatible Armbian box, copy this `led` directory to the box and run:

```sh
sudo ./install-on-box.sh
journalctl -u h96-fd655 -b
python3 h96-fd655.py --dry-run
```

The display has worked on the project box with CLK/DAT mapped according to the Android log. Before manual installation, use `gpioinfo` to confirm `/dev/gpiochip4` is bank GPIO4 and lines 19/20 are available. If digits or icons are misplaced, adjust `grid` and `icon_bits` in `/etc/h96-fd655.json`, then restart the service. `grid` maps the icon and four digits to display RAM; `icon_bits` selects each icon's bit position (0–7).

The Wi-Fi icon stays off until a wireless interface links. FD655 uses GPIO4 and does not control the separate GPIO1 `pwr-wifi` LED. Keeping `armbian-led-state.service` masked for the GPIO38 Wi-Fi workaround does not disable this display.
