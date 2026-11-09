#!/usr/bin/env python3
"""
scripts/attrib.py - `alfi attrib`: who is causing the pressure that `probe` measured.

Three independent signals, one adb round-trip:

  processes  RSS ranking, flagging a single process eating the machine
             (the "Settings Dump Service is using 2 GB" case)
  dexopt     which user-visible apps are still interpreted, so compilation can
             target them instead of a blind list
  alarms     best-effort per-package wakeup counts

Every parser degrades to "unavailable" rather than inventing numbers, because a
tool that reports a confident zero is worse than one that admits ignorance.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

import connect
from ui import ui as get_ui

MARK = "@@"
RUNAWAY_MB = 400          # a single process this large is worth naming
RUNAWAY_SHARE = 0.25      # ...or this share of physical RAM

ATTRIB_CMD = (
    "echo '@@PS'; ps -A -o PID,RSS,NAME 2>/dev/null | head -80; "
    "echo '@@DEXOPT'; dumpsys package dexopt 2>/dev/null | head -400; "
    "echo '@@ALARM'; dumpsys alarm 2>/dev/null | grep -iE '[0-9]+ wakeups' | head -40"
)


# ---------------------------------------------------------------- parsing
def split_sections(raw):
    sections = {}
    current = None
    for line in (raw or "").splitlines():
        if line.startswith(MARK):
            current = line[len(MARK):].strip()
            sections[current] = []
            continue
        if current:
            sections[current].append(line)
    return sections


def parse_ps(block):
    """[{'pid': int, 'rss_mb': float, 'name': str}, ...] sorted by RSS."""
    rows = []
    for line in block or []:
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        pid, rss, name = parts
        if not pid.isdigit() or not rss.isdigit():
            continue
        rows.append({"pid": int(pid), "rss_mb": round(int(rss) / 1024.0, 1), "name": name.strip()})
    rows.sort(key=lambda r: r["rss_mb"], reverse=True)
    return rows


def flag_runaways(rows, total_gb=0.0):
    """Mark the processes big enough to explain a stall, with a reason."""
    limit = max(RUNAWAY_MB, (total_gb * 1024.0) * RUNAWAY_SHARE) if total_gb else RUNAWAY_MB
    flagged = []
    for row in rows:
        if row["rss_mb"] >= limit:
            row = dict(row)
            row["reason"] = "%.0f MB > %.0f MB limit" % (row["rss_mb"], limit)
            flagged.append(row)
    return flagged


def parse_dexopt(block):
    """{'packages': {pkg: {'status':.., 'reason':..}}, 'counts': {...}}."""
    packages = {}
    pkg = None
    for line in block or []:
        text = line.strip()
        if not text:
            continue
        if text.endswith(":") and "." in text and " " not in text:
            pkg = text[:-1]
            continue
        if pkg and "status=" in text:
            status = re.search(r"status=([\w-]+)", text)
            reason = re.search(r"reason=([\w-]+)", text)
            packages[pkg] = {
                "status": status.group(1) if status else "unknown",
                "reason": reason.group(1) if reason else "",
            }
            pkg = None

    counts = {}
    for meta in packages.values():
        counts[meta["status"]] = counts.get(meta["status"], 0) + 1
    return {"packages": packages, "counts": counts}


def parse_alarms(block):
    """[{'wakeups': int, 'package': str}] best effort, newest format first."""
    found = {}
    pattern = re.compile(r"(\d+)\s+wakeups?:\s+\S+\s+([A-Za-z0-9_.]+)")
    for line in block or []:
        match = pattern.search(line)
        if match:
            pkg = match.group(2)
            found[pkg] = max(found.get(pkg, 0), int(match.group(1)))
    rows = [{"package": k, "wakeups": v} for k, v in found.items()]
    rows.sort(key=lambda r: r["wakeups"], reverse=True)
    return rows


def collect(serial=None):
    prefix = ["-s", serial] if serial else []
    ok, raw = connect.run_adb(prefix + ["shell", ATTRIB_CMD], timeout=20)
    if not ok or not raw:
        return {"error": raw or "no output from device"}

    sections = split_sections(raw)
    processes = parse_ps(sections.get("PS"))
    dexopt = parse_dexopt(sections.get("DEXOPT"))
    alarms = parse_alarms(sections.get("ALARM"))

    return {
        "processes": processes[:15],
        "runaways": flag_runaways(processes),
        "dexopt": dexopt,
        "alarms": alarms[:10],
        "alarms_available": bool(alarms),
    }


# ---------------------------------------------------------------- render
def render(ui, data, width=None):
    width = width or ui.width
    if "error" in data:
        return ui.box(["device unreachable: " + str(data["error"])], width=width, title="ATTRIB")

    t = ui.theme
    from ui.widgets import panel, pad

    rows = []
    runaways = data.get("runaways") or []
    rows.append(t.paint("RUNAWAY PROCESSES", "title"))
    if runaways:
        for item in runaways[:4]:
            rows.append(" " + pad(item["name"], 34) + " %7.1f MB  " % item["rss_mb"]
                        + t.paint(item["reason"], "danger"))
    else:
        rows.append(t.paint(" none above the size threshold", "muted"))

    rows.append("")
    rows.append(t.paint("DEXOPT STATE", "title"))
    counts = (data.get("dexopt") or {}).get("counts") or {}
    if counts:
        total = sum(counts.values())
        compiled = counts.get("speed", 0) + counts.get("speed-profile", 0)
        rows.append(" " + pad("%d packages" % total, 34)
                    + " %d compiled (%.0f%%)" % (compiled, 100.0 * compiled / total))
        laggards = [p for p, m in (data["dexopt"]["packages"]).items() if m["status"] == "verify"]
        if laggards:
            rows.append(" " + t.paint("still interpreted: " + ", ".join(laggards[:4]), "warn"))
            rows.append(" " + t.paint("fix: alfi dexopt --targets", "muted"))
    else:
        rows.append(t.paint(" unavailable on this build", "muted"))

    rows.append("")
    rows.append(t.paint("WAKEUPS", "title"))
    if data.get("alarms_available"):
        for item in (data.get("alarms") or [])[:5]:
            rows.append(" " + pad(item["package"], 40) + " %5d wakeups" % item["wakeups"])
    else:
        rows.append(t.paint(" unavailable (alarm dump format not recognised)", "muted"))

    return panel(rows, width, theme=t, title="ATTRIBUTION", ascii_mode=not ui.caps.unicode)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="alfi attrib", description="Who is causing the stalls")
    parser.add_argument("--device", help="adb serial")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    data = collect(args.device)
    if args.json:
        print(json.dumps(data, indent=2))
        return 0 if "error" not in data else 1

    ui = get_ui()
    for line in render(ui, data):
        print(line)
    return 0 if "error" not in data else 1


if __name__ == "__main__":
    sys.exit(main())
