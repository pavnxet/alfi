#!/usr/bin/env python3
"""
scripts/tweak_ui.py - 2x UI Animation Speedup & Cache Maintenance Tool

Tunes Android window, transition, and animator scales to 0.5x (or custom)
and trims stale system caches for instantaneous UI responsiveness.
"""

import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from connect import run_adb, get_connected_devices, get_device_info

def set_animation_scale(scale="0.5", serial=None):
    """Set window, transition, and animator duration scales."""
    prefix = ["-s", serial] if serial else []
    keys = ["window_animation_scale", "transition_animation_scale", "animator_duration_scale"]
    
    print(f"[*] Setting animation scales to {scale}x...")
    for k in keys:
        run_adb(prefix + ["shell", f"settings put global {k} {scale}"])
        print(f"  ✅ {k} -> {scale}")

def trim_system_cache(serial=None):
    """Trim system caches safely."""
    prefix = ["-s", serial] if serial else []
    print("[*] Trimming stale system caches...")
    ok, out = run_adb(prefix + ["shell", "pm trim-caches 1000G"])
    if ok:
        print("  ✅ Cache trimmed successfully.")
    else:
        print(f"  ⚠️ Cache trim result: {out}")

def main():
    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    if not auth:
        print("❌ No authorized Android device connected. Run 'python scripts/connect.py' first.")
        sys.exit(1)

    target_serial = auth[0]["serial"]
    info = get_device_info(target_serial)

    print("\n" + "="*65)
    print(f" ⚡ UI RESPONSIVENESS & ANIMATION TUNER: {info['brand'].upper()} {info['model']}")
    print("="*65)

    scale = "0.5"
    trim = True

    # Parse arguments
    for idx, arg in enumerate(sys.argv):
        if arg.startswith("--scale="):
            scale = arg.split("=")[1]
        elif arg == "--scale" and idx + 1 < len(sys.argv):
            scale = sys.argv[idx + 1]
        elif arg == "--no-trim":
            trim = False

    set_animation_scale(scale, target_serial)
    
    if trim:
        trim_system_cache(target_serial)

    print("\n" + "="*65)
    print(" ✅ UI TUNING COMPLETE! Gestures and app transitions are now significantly faster.")
    print("="*65 + "\n")

if __name__ == "__main__":
    main()
