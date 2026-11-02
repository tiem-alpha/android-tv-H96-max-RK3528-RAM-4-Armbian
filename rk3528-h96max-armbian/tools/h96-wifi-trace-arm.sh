#!/bin/bash
# Finish filtering kernel boot tracing before modules-load, without boot waits.
set -eu
export PATH=/usr/sbin:/usr/bin:/sbin:/bin
trace=/sys/kernel/tracing
mkdir -p /run/h96-wifi-boot-trace "$trace"
mountpoint -q "$trace" || mount -t tracefs tracefs "$trace"
exec >> /run/h96-wifi-boot-trace/arm.log 2>&1
cat /proc/uptime
cat /proc/cmdline
# Boot-time GPIO/clock/pinmux events are already enabled by kernel arguments.
# Exclude the high-rate display pins; preserve all other GPIO activity.
for event in gpio_value gpio_direction; do
    echo 'gpio != 147 && gpio != 148' > "$trace/events/gpio/$event/filter"
done
for event in mmc_request_start mmc_request_done; do
    echo 'name == "mmc2"' > "$trace/events/mmc/$event/filter"
    echo 1 > "$trace/events/mmc/$event/enable"
done
echo 1 > "$trace/tracing_on"
# Argument layouts checked against matching ARM64 6.1.172 headers/source.
# Kprobe fetch faults are recorded as unavailable values; no register writes.
while IFS= read -r spec; do
    [[ -n $spec ]] || continue
    if echo "$spec" >> "$trace/kprobe_events"; then
        event=${spec%% *}
        event=${event#p:h96_wifi/}
        echo 1 > "$trace/events/h96_wifi/$event/enable"
    else
        echo "Optional argument probe unavailable: $spec"
    fi
done < /usr/local/share/h96-wifi-trace-probes.txt
echo 'H96_FILTERS_READY_BEFORE_MODULES' > "$trace/trace_marker"
