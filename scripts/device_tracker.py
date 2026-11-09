#!/usr/bin/env python3
"""
scripts/device_tracker.py - Multi-Device Audit & History Tracker

Automatically fingerprints connected Android devices using physical hardware serials
and Android IDs to prevent collision when multiple phones share the same model name.
Maintains persistent audit logs, past fixes, package manifests, and custom friendly aliases.
"""

import sys
import os
import json
from datetime import datetime

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from connect import run_adb, get_connected_devices, get_device_info

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEVICES_DIR = os.path.join(BASE_DIR, "devices")

def get_device_fingerprint(target_serial=None):
    """
    Extract immutable physical identifiers:
    - ro.serialno (hardware chip serial)
    - android_id (OS installation identifier)
    """
    prefix = ["-s", target_serial] if target_serial else []
    
    # 1. Hardware serial number
    ok, serial_no = run_adb(prefix + ["shell", "getprop ro.serialno"])
    serial_no = serial_no.strip() if ok and serial_no.strip() else "UNKNOWN_SERIAL"

    # 2. Android ID
    ok, android_id = run_adb(prefix + ["shell", "settings get secure android_id"])
    android_id = android_id.strip() if ok and android_id.strip() else "UNKNOWN_ANDROID_ID"

    info = get_device_info(target_serial)
    
    # Collision-proof unique slug: Brand_Model_Last6OfSerial
    short_serial = serial_no[-6:] if len(serial_no) >= 6 else (android_id[:6] if len(android_id) >= 6 else "DEVICE")
    safe_brand = info["brand"].replace(" ", "_").upper()
    safe_model = info["model"].replace(" ", "_").upper()
    device_slug = f"{safe_brand}_{safe_model}_{short_serial}"

    return {
        "device_slug": device_slug,
        "hardware_serial": serial_no,
        "android_id": android_id,
        "brand": info["brand"],
        "model": info["model"],
        "manufacturer": info["manufacturer"],
        "android_version": info["android_version"],
        "sdk_level": info["sdk_level"],
        "build_id": info["build_id"],
        "security_patch": info["security_patch"],
        "target_serial": target_serial
    }

def get_device_dir(device_slug):
    """Return device directory path."""
    return os.path.join(DEVICES_DIR, device_slug)

def load_device_profile(device_slug):
    """Load profile.json for a tracked device."""
    dev_dir = get_device_dir(device_slug)
    profile_path = os.path.join(dev_dir, "profile.json")
    if os.path.exists(profile_path):
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_device_profile(profile):
    """Save or update profile.json."""
    dev_dir = get_device_dir(profile["device_slug"])
    os.makedirs(dev_dir, exist_ok=True)
    profile_path = os.path.join(dev_dir, "profile.json")
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)

def log_device_action(device_slug, action_type, description, details=None):
    """
    Append an audit entry to history.json and history.md in the device's folder.
    """
    dev_dir = get_device_dir(device_slug)
    os.makedirs(dev_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "timestamp": timestamp,
        "action_type": action_type,
        "description": description,
        "details": details or {}
    }

    # 1. Update history.json
    history_json_path = os.path.join(dev_dir, "history.json")
    history = []
    if os.path.exists(history_json_path):
        try:
            with open(history_json_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    
    history.append(entry)
    with open(history_json_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    # 2. Update history.md
    history_md_path = os.path.join(dev_dir, "history.md")
    md_header = ""
    if not os.path.exists(history_md_path):
        profile = load_device_profile(device_slug)
        name = profile.get("assigned_name", device_slug) if profile else device_slug
        md_header = f"# Device Audit & Optimization History — {name}\n\n"
        md_header += f"- **Unique Identifier (Slug)**: `{device_slug}`\n"
        if profile:
            md_header += f"- **Hardware Serial**: `{profile.get('hardware_serial')}`\n"
            md_header += f"- **Android ID**: `{profile.get('android_id')}`\n"
            md_header += f"- **Model / Brand**: {profile.get('brand')} {profile.get('model')}\n"
            md_header += f"- **Android Version**: Android {profile.get('android_version')} (SDK {profile.get('sdk_level')})\n\n"
        md_header += "---\n\n"

    new_section = f"### 🗓️ {timestamp} — {action_type}\n"
    new_section += f"**Summary**: {description}\n\n"
    
    if details:
        if "disabled_packages" in details and details["disabled_packages"]:
            new_section += "**Frozen / Quarantined Packages**:\n"
            for p in details["disabled_packages"]:
                new_section += f"- `{p}`\n"
            new_section += "\n"
        
        if "metrics_before" in details and "metrics_after" in details:
            new_section += "**Performance Metrics**:\n"
            new_section += f"- RAM Available: {details['metrics_before'].get('ram_free', 'N/A')} ➡️ **{details['metrics_after'].get('ram_free', 'N/A')}**\n"
            new_section += f"- ZRAM Swap Used: {details['metrics_before'].get('swap_used', 'N/A')} ➡️ **{details['metrics_after'].get('swap_used', 'N/A')}**\n"
            new_section += f"- Animation Scales: {details['metrics_after'].get('animation_scale', '0.5x')}\n\n"

        if "manifest_path" in details:
            new_section += f"**Backup Manifest**: `{details['manifest_path']}`\n\n"

    new_section += "---\n\n"

    with open(history_md_path, "a", encoding="utf-8") as f:
        if md_header:
            f.write(md_header)
        f.write(new_section)

def list_all_devices():
    """List all registered devices in the devices/ directory."""
    if not os.path.exists(DEVICES_DIR):
        print("📁 No devices have been audited yet.")
        return

    folders = [f for f in os.listdir(DEVICES_DIR) if os.path.isdir(os.path.join(DEVICES_DIR, f))]
    if not folders:
        print("📁 No devices registered in devices/ directory.")
        return

    print("\n" + "="*70)
    print(" 📱 REGISTERED DEVICE AUDIT VAULT")
    print("="*70)
    for idx, slug in enumerate(folders, 1):
        prof = load_device_profile(slug)
        if prof:
            name = prof.get("assigned_name", slug)
            brand = prof.get("brand", "Unknown")
            model = prof.get("model", "Unknown")
            serial = prof.get("hardware_serial", "Unknown")
            created = prof.get("first_registered", "Unknown")
            print(f"[{idx}] {name}")
            print(f"    • ID Slug    : {slug}")
            print(f"    • Hardware   : {brand} {model} (Serial: {serial})")
            print(f"    • Registered : {created}")
            print(f"    • Vault Path : devices/{slug}/history.md")
        else:
            print(f"[{idx}] {slug} (Incomplete profile)")
        print("-" * 60)
    print()

def inspect_connected_device():
    """Detect connected device and show previous fix history."""
    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    if not auth:
        print("❌ No authorized Android device connected. Run 'python scripts/connect.py' first.")
        sys.exit(1)

    target_serial = auth[0]["serial"]
    fp = get_device_fingerprint(target_serial)
    slug = fp["device_slug"]
    prof = load_device_profile(slug)

    print("\n" + "="*70)
    print(f" 🔍 DEVICE RECOGNITION: {fp['brand'].upper()} {fp['model']}")
    print("="*70)
    print(f"  • Hardware Serial   : {fp['hardware_serial']}")
    print(f"  • Android ID        : {fp['android_id']}")
    print(f"  • Unique Device Slug: {slug}")

    if prof:
        print(f"\n✅ WELCOME BACK! Recognized device: '{prof.get('assigned_name', slug)}'")
        print(f"  • First Audited  : {prof.get('first_registered', 'Unknown')}")
        print(f"  • Last Fix Run   : {prof.get('last_updated', 'Unknown')}")
        
        # Load past history
        hist_path = os.path.join(get_device_dir(slug), "history.json")
        if os.path.exists(hist_path):
            with open(hist_path, "r", encoding="utf-8") as f:
                hist = json.load(f)
            print(f"\n📋 PAST FIXES APPLIED ({len(hist)} session(s) recorded):")
            for idx, h in enumerate(hist, 1):
                print(f"  [{idx}] {h['timestamp']} — {h['action_type']}")
                print(f"      {h['description']}")
        print(f"\n👉 Full history viewable at: devices/{slug}/history.md")
    else:
        print(f"\n✨ NEW DEVICE DETECTED!")
        print(f"  This device has not been registered in devices/ yet.")
        print(f"  Suggested Name: '{fp['brand'].capitalize()} {fp['model']} (#{fp['hardware_serial'][-4:]})'")
    print("="*70 + "\n")

def main():
    os.makedirs(DEVICES_DIR, exist_ok=True)

    if len(sys.argv) > 1:
        if sys.argv[1] == "--list":
            list_all_devices()
            return
        elif sys.argv[1] == "--status":
            inspect_connected_device()
            return

    inspect_connected_device()

if __name__ == "__main__":
    main()
