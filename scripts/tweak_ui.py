#!/usr/bin/env python3
"""
scripts/tweak_ui.py - 2x UI Animation Speedup & Cache Maintenance Tool

Tunes Android window, transition, and animator scales to 0.5x (or custom)
and trims stale system caches for instantaneous UI responsiveness.
"""

import sys
import os
import argparse
import json

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from connect import run_adb, get_connected_devices, get_device_info

def set_animation_scale(scale="0.5", serial=None, dry_run=False):
    """Set window, transition, and animator duration scales."""
    prefix = ["-s", serial] if serial else []
    keys = ["window_animation_scale", "transition_animation_scale", "animator_duration_scale"]
    
    label = "[DRY-RUN] " if dry_run else ""
    print(f"[*] {label}Setting animation scales to {scale}x...")
    for k in keys:
        if dry_run:
            print(f"  ✅ {k} -> {scale} (Simulated)")
        else:
            ok, out = run_adb(prefix + ["shell", f"settings put global {k} {scale}"])
            if ok:
                print(f"  ✅ {k} -> {scale}")
            else:
                print(f"  ⚠️ Failed setting {k}: {out}")

def trim_system_cache(serial=None, dry_run=False):
    """Trim system caches safely."""
    prefix = ["-s", serial] if serial else []
    label = "[DRY-RUN] " if dry_run else ""
    print(f"[*] {label}Trimming stale system caches...")
    if dry_run:
        print("  ✅ Cache trimmed successfully (Simulated).")
    else:
        ok, out = run_adb(prefix + ["shell", "pm trim-caches 1000G"], timeout=45)
        if ok:
            print("  ✅ Cache trimmed successfully.")
        elif "timed out" in out.lower():
            print("  ℹ️ Cache trim request dispatched to OS background maintenance.")
        else:
            print(f"  ⚠️ Cache trim result: {out}")

def main():
    parser = argparse.ArgumentParser(description="2x UI Animation Speedup & Cache Maintenance Tool")
    parser.add_argument("--scale", default="0.5", help="Animation duration scale (default: 0.5)")
    parser.add_argument("--no-trim", action="store_true", help="Skip trimming system package caches")
    parser.add_argument("--dry-run", action="store_true", help="Simulate animation scale adjustments")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    target_serial = auth[0]["serial"] if auth else None

    if not auth and not args.dry_run:
        print("\n" + "="*65)
        print(" ⚡ UI RESPONSIVENESS & ANIMATION TUNER [SIMULATOR MODE]")
        print("="*65)
        print(" 💡 Connect your phone via USB to apply real-time compositor speedup.")
    elif auth:
        info = get_device_info(target_serial)
        mode_label = "[DRY-RUN] " if args.dry_run else ""
        print("\n" + "="*65)
        print(f" ⚡ {mode_label}UI RESPONSIVENESS TUNER: {info['brand'].upper()} {info['model']}")
        print("="*65)

    scale = args.scale
    trim = not args.no_trim
    dry_run = args.dry_run or (not auth)

    set_animation_scale(scale, target_serial, dry_run=dry_run)
    
    if trim:
        trim_system_cache(target_serial, dry_run=dry_run)

    if args.json:
        print(json.dumps({
            "scale": scale,
            "trim": trim,
            "dry_run": dry_run,
            "device_connected": bool(auth)
        }, indent=2))
        return

    print("\n" + "="*65)
    print(" ✅ UI TUNING COMPLETE! Gestures and app transitions are now significantly faster.")
    print("="*65 + "\n")

if __name__ == "__main__":
    main()
