#!/usr/bin/env python3
"""
scripts/monitor.py - `alfi watch`: a live, graphical terminal monitor.

One ADB round-trip per tick, rendered as meters and a sparkline. Non-TTY
(pipe, CI, log file) prints a single snapshot and exits, so it is safe to
script and never loops where nobody is watching.
"""

from __future__ import annotations

import argparse
import json
import sys
import time

import connect
from ui import ui as get_ui
from ui.widgets import gauge, panel, sparkline

SNAPSHOT_CMD = (
    "cat /proc/loadavg; "
    "grep -E 'MemTotal|MemAvailable|SwapTotal|SwapFree' /proc/meminfo; "
    "dumpsys battery | grep -E 'level:|temperature:'; "
    "dumpsys cpuinfo | head -6"
)


def _numbers(text, key):
    for line in (text or "").splitlines():
        if key in line:
            digits = "".join(ch if (ch.isdigit() or ch == ".") else " " for ch in line)
            for token in digits.split():
                try:
                    return float(token)
                except ValueError:
                    continue
    return None


def snapshot(serial=None):
    """Read CPU, memory, swap, battery and the top CPU process in one call."""
    prefix = ["-s", serial] if serial else []
    ok, out = connect.run_adb(prefix + ["shell", SNAPSHOT_CMD], timeout=8)
    if not ok or not out:
        return {"error": out or "no output"}

    load = []
    first = (out.splitlines() or [""])[0].split()
    for token in first[:3]:
        try:
            load.append(float(token))
        except ValueError:
            break

    mem_total = _numbers(out, "MemTotal") or 0.0
    mem_available = _numbers(out, "MemAvailable") or 0.0
    swap_total = _numbers(out, "SwapTotal") or 0.0
    swap_free = _numbers(out, "SwapFree") or 0.0
    level = _numbers(out, "level:")
    temperature = _numbers(out, "temperature:")

    top = ""
    for line in out.splitlines():
        if "/" in line and "%" in line:
            top = line.strip()
            break

    gb = 1024.0 * 1024.0
    return {
        "load": load,
        "mem_total_gb": round(mem_total / gb, 2),
        "mem_used_gb": round(max(0.0, mem_total - mem_available) / gb, 2),
        "mem_pct": round(100.0 * max(0.0, mem_total - mem_available) / mem_total, 1) if mem_total else 0.0,
        "swap_total_gb": round(swap_total / gb, 2),
        "swap_used_gb": round(max(0.0, swap_total - swap_free) / gb, 2),
        "swap_pct": round(100.0 * max(0.0, swap_total - swap_free) / swap_total, 1) if swap_total else 0.0,
        "battery": int(level) if level is not None else None,
        "temp_c": round(temperature / 10.0, 1) if temperature else None,
        "top": top,
    }


def render(ui, snap, history, width=None):
    """Build the monitor panel. Pure enough to snapshot-test."""
    width = width or ui.width
    if "error" in snap:
        return ui.box(["device unreachable: " + str(snap["error"])], width=width, title="LIVE MONITOR")

    t = ui.theme
    lines = []
    load = snap.get("load") or []
    load_text = " / ".join("%.1f" % v for v in load) if load else "-"
    cpu_role = "ok" if (load and load[0] < 4) else ("warn" if load and load[0] < 8 else "danger")
    lines.append(gauge(load[0] if load else 0, 8, width=18, theme=t,
                       label="CPU LOAD", unit=load_text))
    lines.append(" " + sparkline(history, width=min(width - 4, 48), theme=t, role=cpu_role)
                 + t.paint("  last %d samples" % len(history), "muted"))

    lines.append(gauge(snap.get("mem_used_gb", 0), snap.get("mem_total_gb") or 1, width=18, theme=t,
                       label="MEMORY", unit="%.2f / %.2f GB" % (snap.get("mem_used_gb", 0), snap.get("mem_total_gb", 0))))

    if snap.get("swap_total_gb"):
        lines.append(gauge(snap.get("swap_used_gb", 0), snap.get("swap_total_gb") or 1, width=18, theme=t,
                           label="SWAP/ZRAM", unit="%.2f / %.2f GB" % (snap.get("swap_used_gb", 0), snap.get("swap_total_gb", 0))))
    else:
        lines.append(t.paint("SWAP/ZRAM ", "muted") + " [no swap configured]")

    battery = snap.get("battery")
    if battery is not None:
        lines.append(gauge(battery, 100, width=18, theme=t, label="BATTERY",
                           unit=("+ %.1f C" % snap["temp_c"]) if snap.get("temp_c") else ""))

    if snap.get("top"):
        lines.append(t.paint("TOP ", "muted") + snap["top"][: max(10, width - 8)])

    return panel(lines, width, theme=t, title="ALFI LIVE MONITOR", ascii_mode=not ui.caps.unicode)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="alfi watch", description="Live device monitor")
    parser.add_argument("--interval", type=float, default=1.5, help="seconds between samples")
    parser.add_argument("--count", type=int, default=0, help="samples to take (0 = until Ctrl-C)")
    parser.add_argument("--device", help="adb serial")
    parser.add_argument("--json", action="store_true", help="print one snapshot as JSON and exit")
    args = parser.parse_args(argv)

    ui = get_ui()
    history = []
    live = ui.caps.is_tty and not args.json and args.count == 0

    try:
        while True:
            snap = snapshot(args.device)
            if args.json:
                print(json.dumps(snap, indent=2))
                return 0
            if "error" not in snap and snap.get("load"):
                history.append(snap["load"][0])
                history = history[-48:]

            if live:
                ui.clear()
                ui.print(render(ui, snap, history))
                ui.print(ui.theme.paint(" ctrl-c to stop", "muted"))
            else:
                for line in render(ui, snap, history):
                    print(line)

            if not live:
                return 0
            time.sleep(max(0.2, args.interval))
            if args.count and len(history) >= args.count:
                return 0
    except KeyboardInterrupt:
        ui.print("")
        return 0


if __name__ == "__main__":
    sys.exit(main())
