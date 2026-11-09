#!/usr/bin/env python3
"""
scripts/verify.py - `alfi verify`: did the debloat actually stick?

The known failure mode of every non-root debloater: the command returns success,
the OEM's package manager quietly restores the app after the next reboot or OTA,
and the tool keeps reporting the package as disabled because it never looks
again. This module looks again.

  alfi verify             compare the newest manifest against live device state
  alfi verify --baseline  record boot_id + current states for later comparison
  alfi verify --json      machine-readable result
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import connect
from operations import get_package_state
from ui import ui as get_ui

BACKUPS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backups")
BASELINE = "verify_baseline.json"


def latest_manifest():
    """Newest manifest that actually records packages (not a doze/bench side-file)."""
    candidates = [f for f in glob.glob(os.path.join(BACKUPS, "*.json"))
                  if not f.endswith(BASELINE)]
    usable = []
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and ("packages" in data or "disabled_packages" in data):
            usable.append(path)
    if not usable:
        return None
    usable.sort(key=lambda p: os.path.getmtime(p))
    return usable[-1]


def read_boot_id(serial=None):
    prefix = ["-s", serial] if serial else []
    ok, out = connect.run_adb(prefix + ["shell", "cat /proc/sys/kernel/random/boot_id"], timeout=5)
    return out.strip() if ok and out else None


def manifest_packages(path):
    """[(package, recorded_status)] from a mode manifest or a restore manifest."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    packages = data.get("packages")
    if isinstance(packages, dict):
        return [(pkg, meta.get("status", "applied") if isinstance(meta, dict) else "applied")
                for pkg, meta in packages.items()]
    if isinstance(packages, list):
        return [(pkg, "applied") for pkg in packages]
    return [(pkg, "applied") for pkg in data.get("disabled_packages", [])]


def classify(recorded, current):
    """Map (what we did, what the device says now) to a verdict."""
    if current == "disabled":
        return "held"
    if current in ("enabled", "uninstalled"):
        return "came back"
    if current == "not_found":
        return "gone"
    return "unknown"


def check(path, serial=None, user_id=0):
    results = []
    for pkg, recorded in manifest_packages(path):
        current = get_package_state(pkg, user_id=user_id, serial=serial)
        results.append({
            "package": pkg,
            "recorded": recorded,
            "current": current,
            "verdict": classify(recorded, current),
        })
    return results


def write_baseline(serial=None, user_id=0):
    path = latest_manifest()
    boot_id = read_boot_id(serial)
    payload = {
        "boot_id": boot_id,
        "manifest": os.path.basename(path) if path else None,
        "packages": {},
    }
    if path:
        for pkg, _recorded in manifest_packages(path):
            payload["packages"][pkg] = get_package_state(pkg, user_id=user_id, serial=serial)
    os.makedirs(BACKUPS, exist_ok=True)
    target = os.path.join(BACKUPS, BASELINE)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return target, payload


def render(ui, results, width=None, boot_changed=None):
    width = width or ui.width
    t = ui.theme
    if not results:
        return ui.box(["no manifest found - run a mode first"], width=width, title="VERIFY")

    held = [r for r in results if r["verdict"] == "held"]
    back = [r for r in results if r["verdict"] == "came back"]
    rows = []
    if boot_changed:
        rows.append(t.paint("device rebooted since the baseline - this is the real test", "info"))
    rows.append("%d of %d packages still disabled" % (len(held), len(results)))
    for item in back[:8]:
        rows.append(t.paint("  came back: ", "danger") + item["package"]
                    + t.paint("  (recorded %s, now %s)" % (item["recorded"], item["current"]), "muted"))
    if len(back) > 8:
        rows.append(t.paint("  (+%d more)" % (len(back) - 8), "muted"))
    if back:
        rows.append("")
        rows.append(t.paint("re-apply with: alfi modes --mode <mode>", "muted"))
    return ui.box(rows, width=width, title="VERIFY")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="alfi verify", description="Did the debloat stick?")
    parser.add_argument("--manifest", help="manifest path (default: newest in backups/)")
    parser.add_argument("--baseline", action="store_true", help="record boot_id and states now")
    parser.add_argument("--device", help="adb serial")
    parser.add_argument("--user", type=int, default=0, help="Android user id")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    if args.baseline:
        target, payload = write_baseline(args.device, args.user)
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print("baseline written: %s" % target)
            print("boot_id: %s" % payload["boot_id"])
            print("%d package(s) recorded" % len(payload["packages"]))
        return 0

    path = args.manifest or latest_manifest()
    if not path or not os.path.exists(path):
        print("❌ no manifest found in backups/ - run a mode first", file=sys.stderr)
        return 1

    results = check(path, args.device, args.user)

    boot_changed = None
    baseline_path = os.path.join(BACKUPS, BASELINE)
    if os.path.exists(baseline_path):
        try:
            with open(baseline_path, "r", encoding="utf-8") as f:
                old_boot = json.load(f).get("boot_id")
            current = read_boot_id(args.device)
            boot_changed = bool(old_boot and current and old_boot != current)
        except (OSError, ValueError):
            pass

    if args.json:
        print(json.dumps({"manifest": os.path.basename(path),
                          "boot_changed": boot_changed,
                          "results": results}, indent=2))
    else:
        ui = get_ui()
        for line in render(ui, results, boot_changed=boot_changed):
            print(line)

    return 0 if all(r["verdict"] == "held" for r in results) else 2


if __name__ == "__main__":
    sys.exit(main())
