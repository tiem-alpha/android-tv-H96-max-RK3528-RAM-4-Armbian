#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
[[ $(id -u) -eq 0 ]] || { echo 'Run as root on the H96 Max' >&2; exit 1; }
apt-get update
apt-get install -y python3-libgpiod
install -Dm755 h96-fd655.py /usr/local/lib/h96-fd655.py
install -Dm644 h96-fd655.service /etc/systemd/system/h96-fd655.service
if [[ ! -e /etc/h96-fd655.json ]]; then
    install -Dm644 h96-fd655.json /etc/h96-fd655.json
fi
systemctl daemon-reload
systemctl enable --now h96-fd655.service
