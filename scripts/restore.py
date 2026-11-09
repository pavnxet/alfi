#!/usr/bin/env python3
"""
scripts/restore.py - 1-Click Disaster-Free Package Restoration Tool

Enables previously disabled or uninstalled packages from backup manifests or by specific package ID.
Reinstalls uninstalled system APKs via 'cmd package install-existing' and verifies restored state.
"""

import sys
import os
import glob
import json
import argparse
from typing import Optional

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from connect import run_adb, get_connected_devices, get_device_info
from operations import apply_package_state

def get_latest_manifest() -> Optional[str]:
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
    parser = argparse.ArgumentParser(description="1-Click Disaster-Free Package Restoration Tool")
    parser.add_argument("--manifest", help="Manifest path or 'latest'")
    parser.add_argument("--package", help="Specific package name to restore")
    parser.add_argument("--dry-run", action="store_true", help="Preview restore actions without modifying device state")
    parser.add_argument("--user", type=int, default=0, help="Android user profile ID (default: 0)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    if not auth:
        latest = get_latest_manifest()
        if args.json:
            print(json.dumps({
                "device_connected": False,
                "latest_manifest": latest
            }, indent=2))
        else:
            print("\n" + "="*70)
            print(" 🔄 1-CLICK ROLLBACK & RESTORATION [STANDALONE CONSOLE]")
            print("="*70)
            if latest:
                with open(latest, "r", encoding="utf-8") as f:
                    m_data = json.load(f)
                pkgs = m_data.get("disabled_packages", m_data.get("packages", []))
                print(f"  • Latest Snapshot  : backups/{os.path.basename(latest)}")
                print(f"  • Snapshot Date    : {m_data.get('timestamp')}")
                print(f"  • Restorable Apps  : {len(pkgs)} package(s)")
            else:
                print("  • No previous restore snapshots found in backups/.")
            print("\n 💡 Plug in your phone via USB or Wireless Debugging to execute 1-click restore.")
            print("="*70 + "\n")
        return

    target_serial = auth[0]["serial"]
    info = get_device_info(target_serial)
    raw_sdk = info.get("sdk_level", 31)
    sdk_level = int(raw_sdk) if raw_sdk and str(raw_sdk).isdigit() else 31

    if not args.json:
        print("\n" + "="*70)
        mode_label = "[DRY-RUN PREVIEW] " if args.dry_run else ""
        print(f" 🔄 {mode_label}PACKAGE RESTORATION: {info['brand'].upper()} {info['model']} (User {args.user})")
        print("="*70)

    # Option 1: Restore single package
    if args.package:
        target_pkg = args.package.strip()
        if not args.json:
            print(f"[*] Restoring package: {target_pkg}...")
        ok, msg = apply_package_state(
            pkg=target_pkg,
            want="enabled",
            user_id=args.user,
            serial=target_serial,
            sdk_level=sdk_level,
            dry_run=args.dry_run
        )
        if args.json:
            print(json.dumps({"package": target_pkg, "success": ok, "message": msg}, indent=2))
        else:
            if ok:
                print(f"  ✅ {msg}")
            else:
                print(f"  ❌ {msg}")
        return

    # Option 2: Restore from manifest
    manifest_arg = args.manifest or "latest"
    if manifest_arg.lower() == "latest":
        manifest_file = get_latest_manifest()
        if not manifest_file:
            print("❌ No restore manifests found in backups/ directory.")
            sys.exit(1)
    else:
        manifest_file = manifest_arg
        if not os.path.exists(manifest_file):
            print(f"❌ Manifest file not found: {manifest_file}")
            sys.exit(1)

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    pkgs = manifest_data.get("disabled_packages", [])
    if not pkgs:
        print("ℹ️ Manifest contains no disabled packages to restore.")
        return

    if not args.json:
        print(f"[*] Loaded manifest: {os.path.basename(manifest_file)}")
        print(f"    Recorded on   : {manifest_data.get('timestamp')}")
        print(f"    Target packages : {len(pkgs)}\n")

    results = []
    restored_count = 0
    for p in pkgs:
        ok, msg = apply_package_state(
            pkg=p,
            want="enabled",
            user_id=args.user,
            serial=target_serial,
            sdk_level=sdk_level,
            dry_run=args.dry_run
        )
        results.append({"package": p, "success": ok, "message": msg})
        if ok:
            restored_count += 1
            if not args.json:
                print(f"  ✅ {msg}")
        else:
            if not args.json:
                print(f"  ⚠️ {msg}")

    if args.json:
        print(json.dumps({
            "dry_run": args.dry_run,
            "manifest": manifest_file,
            "restored_count": restored_count,
            "total_packages": len(pkgs),
            "results": results
        }, indent=2))
        return

    print(f"\n[+] Successfully restored {restored_count} / {len(pkgs)} package(s).")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
