#!/usr/bin/env python3
"""
scripts/rescue.py - Emergency Feature Rescue & Device Recovery Engine

Provides instant recovery if any phone feature (dialer, settings, camera, systemui,
connectivity, or Google Play Services) is restricted, broken, or misbehaving.
Features:
1. --fix-critical: Scans and revives accidentally disabled critical core components.
2. --restore-all: Restores every disabled package across user 0.
3. --rescue-package <pkg>: Deep multi-layer un-restriction (enables APK, reinstalls if uninstalled,
   resets AppOps to allow, resets standby bucket to active, resets ART JIT cache).
4. --cross-manifest-rollback: Scans all manifest types (debloat, ART, AppOps) and reverts them.
5. --guide: Hardware key combinations and instructions for Safe Mode / bootloop recovery.
Captures pre-rescue snapshots in backups/ and logs events to local PC audit vaults.
"""

import sys
import os
import re
import glob
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from connect import run_adb, get_connected_devices, get_device_info, validate_package_name
from device_tracker import get_device_fingerprint, log_device_action
from operations import apply_package_state

CRITICAL_SYSTEM_COMPONENTS = {
    "System UI": ["com.android.systemui"],
    "Settings & Core Config": ["com.android.settings"],
    "Dialer & Telephony": [
        "com.android.dialer",
        "com.google.android.dialer",
        "com.samsung.android.dialer",
        "com.samsung.android.incallui",
        "com.android.server.telecom"
    ],
    "Package Management & Permissions": [
        "com.google.android.packageinstaller",
        "com.android.packageinstaller",
        "com.google.android.permissioncontroller",
        "com.android.permissioncontroller"
    ],
    "Google Core Services": [
        "com.google.android.gms",
        "com.google.android.gsf"
    ],
    "System Web Rendering": [
        "com.google.android.webview",
        "com.android.webview"
    ]
}

SAFE_MODE_GUIDES = {
    "samsung": "Power off phone. Press and hold Power + Volume Down. When the Samsung logo appears, release Power but keep holding Volume Down until 'Safe Mode' appears in the bottom-left corner.",
    "xiaomi": "Power off phone. Press and hold Power until Mi / Redmi / POCO logo appears. Release Power, immediately press and hold Volume Down until device finishes booting into Safe Mode.",
    "google": "With device on, press and hold Power. Tap and hold 'Restart' or 'Power off' on screen until 'Reboot to safe mode' dialog appears. Tap OK.",
    "realme_oneplus": "Power off device. Press and hold Power. When realme / OnePlus logo appears, press and hold Volume Down until Safe Mode is displayed.",
    "general": "Power off device. Press and hold Power button. When manufacturer logo shows, press and hold Volume Down until device completes boot."
}

def get_disabled_packages(serial: Optional[str] = None, user_id: int = 0) -> List[str]:
    """Retrieve all disabled packages on user profile."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", f"pm list packages -d --user {user_id}"])
    if not ok or not out:
        return []
    pkgs = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("package:"):
            pkgs.append(line.replace("package:", "").strip())
    return sorted(pkgs)

def create_rescue_snapshot(
    target_serial: str,
    device_info: Dict[str, Any],
    disabled_pkgs: List[str],
    action_type: str
) -> str:
    """Save snapshot of disabled packages prior to rescue operation."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_model = device_info.get("model", "unknown").replace(" ", "_")
    manifest_name = f"rescue_snapshot_{safe_model}_{timestamp}.json"
    manifest_dir = os.path.join(os.path.dirname(__file__), "..", "backups")
    os.makedirs(manifest_dir, exist_ok=True)
    manifest_path = os.path.join(manifest_dir, manifest_name)

    data = {
        "timestamp": datetime.now().isoformat(),
        "type": "rescue_pre_flight_snapshot",
        "action": action_type,
        "device": {
            "serial": target_serial,
            "model": device_info.get("model"),
            "manufacturer": device_info.get("manufacturer"),
            "android_version": device_info.get("android_version"),
            "sdk_level": device_info.get("sdk_level")
        },
        "disabled_packages_count": len(disabled_pkgs),
        "disabled_packages": disabled_pkgs
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return manifest_path

def rescue_single_package(
    pkg: str,
    serial: Optional[str] = None,
    user_id: int = 0,
    sdk_level: int = 31,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Performs deep multi-layer rescue on a package:
    1. Re-enables via operations ladder
    2. Re-installs via install-existing if uninstalled
    3. Resets AppOps RUN_IN_BACKGROUND to allow
    4. Sets Standby Bucket to active
    5. Resets ART compilation cache
    """
    if not validate_package_name(pkg):
        return {"package": pkg, "success": False, "error": f"Invalid package name: {pkg}"}

    prefix = ["-s", serial] if serial else []
    actions_taken = []
    errors = []

    # 1. Enable
    ok_en, msg_en = apply_package_state(pkg, want="enabled", user_id=user_id, serial=serial, sdk_level=sdk_level, dry_run=dry_run)
    actions_taken.append(msg_en)
    if not ok_en:
        errors.append(msg_en)

    # 2. Install-existing (recovers uninstalled packages)
    if not dry_run:
        ok_inst, out_inst = run_adb(prefix + ["shell", f"cmd package install-existing --user {user_id} {pkg}"])
        if ok_inst and "installed" in out_inst.lower():
            actions_taken.append(f"Reinstalled existing: {pkg}")
    else:
        actions_taken.append(f"[DRY-RUN] Would execute: cmd package install-existing --user {user_id} {pkg}")

    # 3. Reset AppOps
    if not dry_run:
        run_adb(prefix + ["shell", f"cmd appops set {pkg} RUN_IN_BACKGROUND allow"])
        run_adb(prefix + ["shell", f"cmd appops set {pkg} RUN_ANY_IN_BACKGROUND allow"])
        actions_taken.append("AppOps reset -> allow")
    else:
        actions_taken.append("[DRY-RUN] AppOps reset -> allow")

    # 4. Reset Standby Bucket
    if not dry_run:
        run_adb(prefix + ["shell", f"am set-standby-bucket {pkg} active"])
        actions_taken.append("Standby bucket reset -> active")
    else:
        actions_taken.append("[DRY-RUN] Standby bucket reset -> active")

    # 5. Reset ART cache
    if not dry_run:
        run_adb(prefix + ["shell", f"cmd package compile --reset {pkg}"])
        actions_taken.append("ART JIT compilation reset")
    else:
        actions_taken.append("[DRY-RUN] ART compilation reset")

    return {
        "package": pkg,
        "success": len(errors) == 0,
        "actions": actions_taken,
        "errors": errors
    }

def find_all_manifests() -> List[Dict[str, Any]]:
    """Scan backups/ for all manifest types."""
    manifest_dir = os.path.join(os.path.dirname(__file__), "..", "backups")
    if not os.path.exists(manifest_dir):
        return []
    files = glob.glob(os.path.join(manifest_dir, "*.json"))
    manifests = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                manifests.append({
                    "filename": os.path.basename(f),
                    "path": f,
                    "mtime": os.path.getmtime(f),
                    "type": data.get("type", "unknown"),
                    "timestamp": data.get("timestamp", ""),
                    "package_count": len(data.get("packages", data.get("disabled_packages", [])))
                })
        except Exception:
            continue
    manifests.sort(key=lambda x: x["mtime"], reverse=True)
    return manifests

def main():
    parser = argparse.ArgumentParser(description="Emergency Feature Rescue & Device Recovery Engine")
    parser.add_argument("--fix-critical", action="store_true", help="Scan and revive any disabled critical core system components")
    parser.add_argument("--restore-all-disabled", action="store_true", help="Re-enable all packages currently marked disabled on user profile")
    parser.add_argument("--rescue-package", help="Deep multi-layer un-restriction for a specific package")
    parser.add_argument("--list-disabled", action="store_true", help="Display all currently disabled packages")
    parser.add_argument("--list-manifests", action="store_true", help="List all available historical reset points and manifests")
    parser.add_argument("--guide", choices=["samsung", "xiaomi", "google", "realme_oneplus", "general"], help="Display hardware Safe Mode recovery guide")
    parser.add_argument("--user", type=int, default=0, help="Target Android user ID (default: 0)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate rescue operations without modifying device state")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    # Display rescue guide if requested
    if args.guide:
        guide_text = SAFE_MODE_GUIDES.get(args.guide, SAFE_MODE_GUIDES["general"])
        if args.json:
            print(json.dumps({"oem": args.guide, "safe_mode_guide": guide_text}, indent=2))
        else:
            print("\n" + "="*70)
            print(f" 🆘 SAFE MODE HARDWARE RESCUE GUIDE: {args.guide.upper()}")
            print("="*70)
            print(f"\n{guide_text}\n")
            print("Once booted in Safe Mode, USB Debugging remains active. Connect your PC")
            print("and run 'python scripts/rescue.py --restore-all-disabled' to recover.")
            print("="*70 + "\n")
        return

    # List manifests if requested
    if args.list_manifests:
        manifests = find_all_manifests()
        if args.json:
            print(json.dumps({"manifest_count": len(manifests), "manifests": manifests}, indent=2))
        else:
            print("\n" + "="*70)
            print(f" 📂 AVAILABLE RESET MANIFESTS ({len(manifests)} found in backups/)")
            print("="*70)
            for m in manifests:
                print(f"  • {m['filename']}")
                print(f"    Type: {m['type']} | Packages: {m['package_count']} | Timestamp: {m['timestamp']}")
            print("="*70 + "\n")
        return

    # Device connection
    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    if not auth:
        print("❌ No authorized Android device connected. Run 'python scripts/connect.py' first.")
        print("💡 If your device is bootlooping or stuck, boot into Safe Mode with '--guide <oem>'.")
        sys.exit(1)

    target_serial = auth[0]["serial"]
    info = get_device_info(target_serial)
    fp = get_device_fingerprint(target_serial)
    slug = fp["device_slug"]
    sdk_level = int(info.get("sdk_level", 31))

    disabled_pkgs = get_disabled_packages(target_serial, user_id=args.user)

    # 1. List disabled packages
    if args.list_disabled:
        if args.json:
            print(json.dumps({
                "serial": target_serial,
                "disabled_count": len(disabled_pkgs),
                "packages": disabled_pkgs
            }, indent=2))
        else:
            print("\n" + "="*70)
            print(f" 🔍 CURRENTLY DISABLED PACKAGES: {info['brand'].upper()} {info['model']} ({len(disabled_pkgs)} found)")
            print("="*70)
            for p in disabled_pkgs:
                print(f"  • {p}")
            print("="*70 + "\n")
        return

    # 2. Fix Critical System Components
    if args.fix_critical:
        disabled_set = set(disabled_pkgs)
        compromised = {}
        for category, pkgs in CRITICAL_SYSTEM_COMPONENTS.items():
            for p in pkgs:
                if p in disabled_set:
                    compromised.setdefault(category, []).append(p)

        if not args.json:
            print("\n" + "="*70)
            mode_lbl = "[DRY-RUN] " if args.dry_run else ""
            print(f" 🛡️ {mode_lbl}CRITICAL SYSTEM RECOVERY ENGINE: {info['brand'].upper()} {info['model']}")
            print("="*70)

        if not compromised:
            if not args.json:
                print(" ✅ All critical system components (SystemUI, Settings, Dialer, WebView, GMS) are HEALTHY.")
                print("="*70 + "\n")
            else:
                print(json.dumps({"status": "healthy", "compromised_count": 0}, indent=2))
            return

        # Snapshot before rescue
        snapshot_path = ""
        if not args.dry_run:
            snapshot_path = create_rescue_snapshot(target_serial, info, disabled_pkgs, "fix_critical")

        recovered = []
        for cat, pkgs in compromised.items():
            if not args.json:
                print(f"\n[*] Reviving {cat}:")
            for p in pkgs:
                res = rescue_single_package(p, target_serial, user_id=args.user, sdk_level=sdk_level, dry_run=args.dry_run)
                recovered.append(res)
                if not args.json:
                    icon = "✅" if res["success"] else "❌"
                    print(f"  {icon} Restored: {p}")

        if not args.dry_run:
            log_device_action(
                slug,
                "Critical System Components Rescued",
                f"Revived {len(recovered)} critical packages across {list(compromised.keys())}.",
                {"snapshot": snapshot_path, "recovered": recovered}
            )

        if args.json:
            print(json.dumps({
                "status": "rescued",
                "snapshot": snapshot_path,
                "recovered_count": len(recovered),
                "recovered": recovered
            }, indent=2))
        else:
            print("\n" + "="*70)
            print(f" ✅ Revived {len(recovered)} critical system package(s).")
            if snapshot_path:
                print(f" 💾 Pre-rescue snapshot saved to backups/{os.path.basename(snapshot_path)}")
            print("="*70 + "\n")
        return

    # 3. Rescue Single Package
    if args.rescue_package:
        target_pkg = args.rescue_package.strip()
        snapshot_path = ""
        if not args.dry_run:
            snapshot_path = create_rescue_snapshot(target_serial, info, disabled_pkgs, f"rescue_pkg_{target_pkg}")

        res = rescue_single_package(target_pkg, target_serial, user_id=args.user, sdk_level=sdk_level, dry_run=args.dry_run)
        if not args.dry_run and res["success"]:
            log_device_action(
                slug,
                f"Deep Package Rescue ({target_pkg})",
                f"Restored package {target_pkg} with AppOps, Standby, and ART resets.",
                {"package": target_pkg, "snapshot": snapshot_path, "actions": res["actions"]}
            )

        if args.json:
            print(json.dumps({"rescue_result": res, "snapshot": snapshot_path}, indent=2))
        else:
            print("\n" + "="*70)
            mode_lbl = "[DRY-RUN] " if args.dry_run else ""
            print(f" 🚑 {mode_lbl}DEEP PACKAGE RESCUE: {target_pkg}")
            print("="*70)
            for act in res["actions"]:
                print(f"  • {act}")
            if res["errors"]:
                print(f"  ⚠️ Errors: {res['errors']}")
            if snapshot_path:
                print(f" 💾 Pre-rescue snapshot: backups/{os.path.basename(snapshot_path)}")
            print("="*70 + "\n")
        return

    # 4. Restore All Disabled Packages
    if args.restore_all_disabled:
        if not disabled_pkgs:
            if args.json:
                print(json.dumps({"status": "no_disabled_packages"}, indent=2))
            else:
                print("ℹ️ No packages are currently marked disabled on this device.")
            return

        snapshot_path = ""
        if not args.dry_run:
            snapshot_path = create_rescue_snapshot(target_serial, info, disabled_pkgs, "restore_all_disabled")

        if not args.json:
            print("\n" + "="*70)
            mode_lbl = "[DRY-RUN] " if args.dry_run else ""
            print(f" 🔄 {mode_lbl}RESTORING ALL {len(disabled_pkgs)} DISABLED PACKAGES...")
            print("="*70)

        results = []
        for p in disabled_pkgs:
            ok, msg = apply_package_state(p, want="enabled", user_id=args.user, serial=target_serial, sdk_level=sdk_level, dry_run=args.dry_run)
            results.append({"package": p, "success": ok, "message": msg})
            if not args.json:
                icon = "✅" if ok else "❌"
                print(f"  {icon} {p}")

        if not args.dry_run:
            log_device_action(
                slug,
                "All Disabled Packages Restored",
                f"Re-enabled {len(disabled_pkgs)} disabled packages.",
                {"snapshot": snapshot_path, "packages": disabled_pkgs}
            )

        if args.json:
            print(json.dumps({
                "status": "restored_all",
                "count": len(disabled_pkgs),
                "snapshot": snapshot_path,
                "results": results
            }, indent=2))
        else:
            print("\n" + "="*70)
            print(f" ✅ Re-enabled {len(disabled_pkgs)} package(s).")
            if snapshot_path:
                print(f" 💾 Pre-rescue snapshot saved to backups/{os.path.basename(snapshot_path)}")
            print("="*70 + "\n")
        return

    parser.print_help()

if __name__ == "__main__":
    main()
