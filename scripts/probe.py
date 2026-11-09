#!/usr/bin/env python3
"""
scripts/probe.py - `alfi probe`: one round-trip measurement of what the phone is
actually waiting on.

The headline signal is PSI (Pressure Stall Information): the share of time tasks
spent stalled on memory, IO or CPU. Android's own lmkd uses the same counters to
decide what to kill, so this is the platform's definition of "slow", not ours.

Everything is read-only and comes back in a single adb shell call.
"""

from __future__ import annotations

import argparse
import json
import math
import sys

import connect
from ui import ui as get_ui

MARK = "@@"

PROBE_CMD = (
    "for r in memory io cpu; do echo '@@PSI ' $r; cat /proc/pressure/$r 2>/dev/null || echo unavailable; done; "
    "echo '@@VMSTAT'; grep -E '^(pswpin|pswpout|pgscan_direct|pgmajfault)' /proc/vmstat 2>/dev/null; "
    "echo '@@THERMAL'; dumpsys thermalservice; "
    "echo '@@BATTERY'; dumpsys battery; "
    "echo '@@MEM'; grep -E '^(MemTotal|MemAvailable|SwapTotal|SwapFree)' /proc/meminfo"
)

THERMAL_NAMES = {
    0: "NONE", 1: "LIGHT", 2: "MODERATE", 3: "SEVERE",
    4: "CRITICAL", 5: "EMERGENCY", 6: "SHUTDOWN",
}


# ---------------------------------------------------------------- parsing
def split_sections(raw):
    """Split the combined shell output into {section: [lines]}."""
    sections = {}
    current = None
    for line in (raw or "").splitlines():
        if line.startswith(MARK):
            name = line[len(MARK):].strip()
            current = name
            sections[current] = []
            continue
        if current:
            sections[current].append(line)
    return sections


def parse_psi(block):
    """{'some': {'avg10': .., 'total': ..}, 'full': {...}} or {} when unsupported."""
    out = {}
    for line in block or []:
        parts = line.split()
        if not parts or parts[0] not in ("some", "full"):
            continue
        fields = {}
        for token in parts[1:]:
            if "=" in token:
                key, value = token.split("=", 1)
                try:
                    fields[key] = float(value)
                except ValueError:
                    pass
        if fields:
            out[parts[0]] = fields
    return out


def parse_vmstat(block):
    """Fallback counters for kernels without PSI."""
    out = {}
    for line in block or []:
        parts = line.split()
        if len(parts) == 2:
            try:
                out[parts[0]] = int(parts[1])
            except ValueError:
                pass
    return out


def parse_thermal(block):
    """Thermal status plus the hottest zones. Honours IsStatusOverride."""
    status = None
    override = False
    zones = []
    for line in block or []:
        text = line.strip()
        if text.startswith("IsStatusOverride:"):
            override = "true" in text.lower()
        elif text.startswith("Thermal Status:"):
            digits = "".join(ch for ch in text if ch.isdigit())
            status = int(digits) if digits else None
        elif "Temperature{" in text:
            name = _field(text, "mName")
            value = _field(text, "mValue")
            if name and value is not None:
                zones.append((name, value))
    # The dump prints cached and live copies of the same zone; keep the hottest.
    hottest = {}
    for name, value in zones:
        if isinstance(value, float) and math.isnan(value):
            continue
        if name not in hottest or value > hottest[name]:
            hottest[name] = value
    ranked = sorted(hottest.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "status": status,
        "status_name": THERMAL_NAMES.get(status, "UNKNOWN") if status is not None else "UNKNOWN",
        "override": override,
        "hottest": ranked[:3],
    }


def _field(text, key):
    marker = key + "="
    start = text.find(marker)
    if start < 0:
        return None
    start += len(marker)
    end = start
    while end < len(text) and text[end] not in ",}":
        end += 1
    token = text[start:end].strip()
    try:
        return float(token)
    except ValueError:
        return token


def parse_battery(block):
    level = temp = None
    for line in block or []:
        text = line.strip()
        if text.startswith("level:"):
            level = _int(text.split(":", 1)[1])
        elif text.startswith("temperature:"):
            raw = _int(text.split(":", 1)[1])
            temp = round(raw / 10.0, 1) if raw is not None else None
    return {"level": level, "temp_c": temp}


def parse_mem(block):
    values = {}
    for line in block or []:
        parts = line.split()
        if len(parts) >= 2 and parts[0].endswith(":"):
            try:
                values[parts[0][:-1]] = float(parts[1])
            except ValueError:
                pass
    total = values.get("MemTotal", 0.0)
    available = values.get("MemAvailable", 0.0)
    swap_total = values.get("SwapTotal", 0.0)
    swap_free = values.get("SwapFree", 0.0)
    gb = 1024.0 * 1024.0
    return {
        "total_gb": round(total / gb, 2),
        "used_gb": round(max(0.0, total - available) / gb, 2),
        "used_pct": round(100.0 * max(0.0, total - available) / total, 1) if total else 0.0,
        "swap_total_gb": round(swap_total / gb, 2),
        "swap_used_gb": round(max(0.0, swap_total - swap_free) / gb, 2),
        "swap_pct": round(100.0 * max(0.0, swap_total - swap_free) / swap_total, 1) if swap_total else 0.0,
    }


def _int(token):
    digits = "".join(ch for ch in str(token) if ch.isdigit() or ch == "-")
    try:
        return int(digits)
    except ValueError:
        return None


def verdict(some_avg60, full_avg60):
    """Map memory PSI to plain language. Thresholds are documented in PLAN_v2."""
    if full_avg60 > 5:
        return "thrashing", "danger"
    if some_avg60 > 20:
        return "severe pressure", "danger"
    if some_avg60 > 5:
        return "real stutter source", "warn"
    if some_avg60 > 1:
        return "mild pressure", "warn"
    return "memory is not the problem", "ok"


def probe(serial=None):
    """Run the combined measurement and return a structured result."""
    prefix = ["-s", serial] if serial else []
    ok, raw = connect.run_adb(prefix + ["shell", PROBE_CMD], timeout=12)
    if not ok or not raw:
        return {"error": raw or "no output from device"}

    sections = split_sections(raw)
    psi = {name: parse_psi(sections.get("PSI " + name) or [])
           for name in ("memory", "io", "cpu")}
    result = {
        "psi": psi,
        "psi_supported": bool(psi.get("memory")),
        "vmstat": parse_vmstat(sections.get("VMSTAT")),
        "thermal": parse_thermal(sections.get("THERMAL")),
        "battery": parse_battery(sections.get("BATTERY")),
        "memory": parse_mem(sections.get("MEM")),
    }
    mem = psi.get("memory") or {}
    some = (mem.get("some") or {}).get("avg60", 0.0)
    full = (mem.get("full") or {}).get("avg60", 0.0)
    label, role = verdict(some, full)
    result["memory_verdict"] = label
    result["memory_verdict_role"] = role
    return result


# ---------------------------------------------------------------- render
def render(ui, data, width=None):
    width = width or ui.width
    if "error" in data:
        return ui.box(["device unreachable: " + str(data["error"])], width=width, title="PROBE")

    t = ui.theme
    rows = []

    if data.get("psi_supported"):
        for resource in ("memory", "io", "cpu"):
            block = data["psi"].get(resource) or {}
            some = block.get("some") or {}
            full = block.get("full") or {}
            line = (pad_label(resource.upper() + " STALL") + " some %5.2f%%  60s %5.2f%%"
                    % (some.get("avg10", 0.0), some.get("avg60", 0.0)))
            if full:
                line += "  full %4.2f%%" % full.get("avg60", 0.0)
            rows.append(line)
        rows.append("")
        rows.append(t.paint("verdict ", "muted") + t.paint(data["memory_verdict"], data["memory_verdict_role"]))
    else:
        vm = data.get("vmstat") or {}
        rows.append(t.paint("PSI unavailable on this kernel - falling back to vmstat", "warn"))
        rows.append(pad_label("swap in/out") + "%s / %s pages" % (vm.get("pswpin", "-"), vm.get("pswpout", "-")))
        rows.append(pad_label("major faults") + str(vm.get("pgmajfault", "-")))

    mem = data.get("memory") or {}
    rows.append("")
    rows.append(pad_label("MEMORY") + "%.2f / %.2f GB used (%.0f%%)"
                % (mem.get("used_gb", 0), mem.get("total_gb", 0), mem.get("used_pct", 0)))
    if mem.get("swap_total_gb"):
        rows.append(pad_label("SWAP/ZRAM") + "%.2f / %.2f GB (%.0f%%)"
                    % (mem.get("swap_used_gb", 0), mem.get("swap_total_gb", 0), mem.get("swap_pct", 0)))

    thermal = data.get("thermal") or {}
    if thermal.get("status") is not None:
        rows.append("")
        if thermal.get("override"):
            rows.append(t.paint("thermal status is OVERRIDDEN by another tool - not a real reading", "warn"))
        else:
            rows.append(pad_label("THERMAL") + "%s (%d)" % (thermal["status_name"], thermal["status"]))
            if thermal.get("hottest"):
                rows.append(pad_label("") + ", ".join("%s %.1fC" % (n, v) for n, v in thermal["hottest"]))

    battery = data.get("battery") or {}
    if battery.get("level") is not None:
        rows.append(pad_label("BATTERY") + "%d%%%s" % (battery["level"],
                                                       ("  %.1fC" % battery["temp_c"]) if battery.get("temp_c") else ""))

    return panel_or_box(ui, rows, width)


def pad_label(text, size=13):
    from ui.widgets import pad
    return pad(text, size)


def panel_or_box(ui, rows, width):
    from ui.widgets import panel
    return panel(rows, width, theme=ui.theme, title="PROBE", ascii_mode=not ui.caps.unicode)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="alfi probe", description="Stall, thermal and memory probe")
    parser.add_argument("--device", help="adb serial")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    data = probe(args.device)
    if args.json:
        print(json.dumps(data, indent=2))
        return 0 if "error" not in data else 1

    ui = get_ui()
    for line in render(ui, data):
        print(line)
    return 0 if "error" not in data else 1


if __name__ == "__main__":
    sys.exit(main())
