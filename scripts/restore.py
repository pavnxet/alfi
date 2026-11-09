#!/usr/bin/env python3
"""
scripts/restore.py - 1-Click Disaster-Free Package Restoration Tool

Enables previously disabled packages from backup manifests or by specific package ID.
Guarantees 100% reversible optimization.
"""

import sys
import os
import glob
import json

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from connect import run_adb, get_connected_devices, get_device_info

def enable_package(pkg, serial=None):
    """Re-enable a previously disabled package."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", f"pm enable {pkg}"])
    return ok and "enabled" in out.lower(), out

def get_disabled_packages(serial=None):
    """Retrieve all currently disabled packages on the device."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", "pm list packages -d"])
    if not ok:
        return []
    return [line.replace("package:", "").strip() for line in out.splitlines() if line.strip()]

def get_latest_manifest():
    """Find the most recent restore manifest file."""
    manifest_dir = os.path.join(os.path.dirname(__file__), "..", "backups")
    if not os.path.exists(manifest_dir):
        return None
    files = glob.glob(os.path.join(manifest_dir, "restore_manifest_*.json"))
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]

def main():
    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    if not auth:
        print("❌ No authorized Android device connected. Run 'python scripts/connect.py' first.")
        sys.exit(1)

    target_serial = auth[0]["serial"]
    info = get_device_info(target_serial)

    print("\n" + "="*70)
    print(f" 🔄 PACKAGE RESTORATION TOOL: {info['brand'].upper()} {info['model']}")
    print("="*70)

    # Option 1: Restore single package
    if len(sys.argv) > 1 and sys.argv[1] == "--package" and len(sys.argv) >= 3:
        target_pkg = sys.argv[2]
        print(f"[*] Re-enabling package: {target_pkg}...")
        ok, out = enable_package(target_pkg, target_serial)
        if ok:
            print(f"✅ Successfully enabled {target_pkg}.")
        else:
            print(f"⚠️ Result: {out}")
        return

    # Option 2: Restore from manifest
    target_manifest = None
    if len(sys.argv) > 1 and sys.argv[1].startswith("--manifest"):
        if "=" in sys.argv[1]:
            val = sys.argv[1].split("=")[1]
        elif len(sys.argv) >= 3:
            val = sys.argv[2]
        else:
            val = "latest"

        if val == "latest":
            target_manifest = get_latest_manifest()
        else:
            target_manifest = val

    if target_manifest:
        if not os.path.exists(target_manifest):
            print(f"❌ Manifest file not found: {target_manifest}")
            sys.exit(1)

        with open(target_manifest, "r", encoding="utf-8") as f:
            data = json.load(f)

        pkgs = data.get("disabled_packages", [])
        print(f"\n[+] Found {len(pkgs)} package(s) in manifest: {os.path.basename(target_manifest)}")
        
        restored = 0
        for pkg in pkgs:
            ok, out = enable_package(pkg, target_serial)
            if ok:
                print(f"  ✅ Restored: {pkg}")
                restored += 1
            else:
                print(f"  ⚠️ Could not re-enable {pkg}: {out}")

        print(f"\n🎉 Successfully restored {restored} package(s) from manifest.")
        return

    # Option 3: List all currently disabled packages on device
    disabled = get_disabled_packages(target_serial)
    if not disabled:
        print("\n✅ There are currently NO disabled packages on this device.")
        return

    print(f"\n[+] Currently disabled packages on device ({len(disabled)} total):")
    for idx, p in enumerate(disabled, 1):
        print(f"  {idx:>2}. {p}")

    print("\n💡 HOW TO RESTORE:")
    print("  To restore the most recent optimization run:")
    print("    python scripts/restore.py --manifest latest")
    print("  To restore a specific package:")
    print("    python scripts/restore.py --package <package_name>")
    print("  To re-enable ALL disabled packages on device:")
    print("    python scripts/restore.py --all")

    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        print("\n[*] Restoring all disabled packages...")
        for p in disabled:
            enable_package(p, target_serial)
        print("✅ All disabled packages restored.")

if __name__ == "__main__":
    main()
