#!/usr/bin/env python3
"""
scripts/appops_restrict.py - Background Execution Limits & App Standby Bucket Manager

Restricts non-essential background execution for apps users wish to keep installed
without completely disabling or uninstalling them.
Controls:
1. AppOps RUN_IN_BACKGROUND and RUN_ANY_IN_BACKGROUND (prevents background service starts & alarms)
2. App Standby Buckets ('restricted' / 'rare' caps background network & job scheduling)
Includes pre-flight snapshot manifests for 1-click restoration.
"""

import sys
import os
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

VALID_BUCKETS = ["active", "working_set", "frequent", "rare", "restricted"]

PRESET_BACKGROUND_HOGS = [
    "com.facebook.katana",
    "com.instagram.android",
    "com.twitter.android",
    "com.snapchat.android",
    "com.eterno",
    "com.amazon.mShop.android.shopping",
    "com.flipkart.android",
    "com.myntra.android",
    "com.truecaller"
]

def get_appops_state(pkg: str, op: str = "RUN_IN_BACKGROUND", serial: Optional[str] = None) -> str:
    """Retrieve current AppOps state for an operation (allow, ignore, deny, default)."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", f"cmd appops get {pkg} {op}"])
    if not ok or not out:
        return "default"
    out_lower = out.lower()
    if "ignore" in out_lower:
        return "ignore"
    if "deny" in out_lower:
        return "deny"
    if "allow" in out_lower:
        return "allow"
    return "default"

def get_standby_bucket(pkg: str, serial: Optional[str] = None) -> str:
    """Retrieve current standby bucket for an app."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", f"am get-standby-bucket {pkg}"])
    if not ok or not out:
        return "active"
    
    val = out.strip().lower()
    # Numeric or string bucket representation
    # 10: active, 20: working_set, 30: frequent, 40: rare, 45: restricted
    bucket_map = {
        "10": "active",
        "20": "working_set",
        "30": "frequent",
        "40": "rare",
        "45": "restricted"
    }
    return bucket_map.get(val, val if val in VALID_BUCKETS else "active")

def set_appops_restriction(
    pkg: str,
    mode: str = "ignore",
    serial: Optional[str] = None,
    dry_run: bool = False
) -> Tuple[bool, str]:
    """
    Apply or remove AppOps background execution restrictions.
    mode in {'ignore', 'allow'}
    """
    if not validate_package_name(pkg):
        return False, f"Invalid package name format: '{pkg}'"

    prefix = ["-s", serial] if serial else []
    ops = ["RUN_IN_BACKGROUND", "RUN_ANY_IN_BACKGROUND"]
    
    if dry_run:
        cmds = [f"cmd appops set {pkg} {op} {mode}" for op in ops]
        return True, f"[DRY-RUN] Would execute: adb shell '{' && '.join(cmds)}'"

    all_ok = True
    errors = []
    for op in ops:
        ok, out = run_adb(prefix + ["shell", f"cmd appops set {pkg} {op} {mode}"])
        if not ok:
            all_ok = False
            errors.append(out)

    if all_ok:
        state_label = "restricted (blocked from background execution)" if mode == "ignore" else "restored (allowed background execution)"
        return True, f"AppOps {pkg} -> {state_label}"
    return False, f"Failed to set AppOps for {pkg}: {'; '.join(errors)}"

def set_standby_bucket(
    pkg: str,
    bucket: str = "restricted",
    serial: Optional[str] = None,
    dry_run: bool = False
) -> Tuple[bool, str]:
    """
    Assign an application to a specific App Standby bucket.
    """
    if not validate_package_name(pkg):
        return False, f"Invalid package name format: '{pkg}'"

    if bucket not in VALID_BUCKETS:
        return False, f"Invalid standby bucket: '{bucket}'. Must be one of {VALID_BUCKETS}"

    prefix = ["-s", serial] if serial else []
    cmd = f"am set-standby-bucket {pkg} {bucket}"

    if dry_run:
        return True, f"[DRY-RUN] Would execute: adb shell {cmd}"

    ok, out = run_adb(prefix + ["shell", cmd])
    if ok:
        return True, f"Standby bucket for {pkg} -> '{bucket}'"
    return False, f"Failed to set standby bucket for {pkg}: {out}"

def create_appops_manifest(
    target_serial: str,
    device_info: Dict[str, Any],
    packages_state: List[Dict[str, Any]]
) -> str:
    """Create pre-flight snapshot manifest preserving original AppOps & bucket states."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_model = device_info.get("model", "unknown").replace(" ", "_")
    manifest_name = f"appops_manifest_{safe_model}_{timestamp}.json"
    manifest_dir = os.path.join(os.path.dirname(__file__), "..", "backups")
    os.makedirs(manifest_dir, exist_ok=True)
    manifest_path = os.path.join(manifest_dir, manifest_name)

    data = {
        "timestamp": datetime.now().isoformat(),
        "type": "appops_standby_reset_point",
        "device": {
            "serial": target_serial,
            "model": device_info.get("model"),
            "manufacturer": device_info.get("manufacturer"),
            "android_version": device_info.get("android_version"),
            "build_id": device_info.get("build_id")
        },
        "packages": packages_state,
        "reset_command": f"python scripts/appops_restrict.py --reset-manifest {manifest_name}"
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return manifest_path

def main():
    parser = argparse.ArgumentParser(description="AppOps Background Restriction & Standby Bucket Manager")
    parser.add_argument("--app", help="Target package name to restrict")
    parser.add_argument("--preset", choices=["social", "all-user"], help="Target predefined background hogs or all third-party user apps")
    parser.add_argument("--mode", default="ignore", choices=["ignore", "allow"], help="AppOps mode (default: ignore)")
    parser.add_argument("--bucket", default="restricted", choices=VALID_BUCKETS, help="Standby bucket to assign (default: restricted)")
    parser.add_argument("--reset-app", help="Restore a specific app back to unrestricted background activity")
    parser.add_argument("--reset-manifest", help="Restore all packages from an AppOps snapshot manifest")
    parser.add_argument("--dry-run", action="store_true", help="Simulate restrictions without modifying device")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    if not auth:
        print("❌ No authorized Android device connected. Run 'python scripts/connect.py' first.")
        sys.exit(1)

    target_serial = auth[0]["serial"]
    info = get_device_info(target_serial)
    fp = get_device_fingerprint(target_serial)
    slug = fp["device_slug"]

    # 1. Reset from manifest
    if args.reset_manifest:
        manifest_path = args.reset_manifest
        if not os.path.exists(manifest_path):
            manifest_path = os.path.join(os.path.dirname(__file__), "..", "backups", args.reset_manifest)
        if not os.path.exists(manifest_path):
            print(f"❌ Manifest not found: {args.reset_manifest}")
            sys.exit(1)

        with open(manifest_path, "r", encoding="utf-8") as f:
            m_data = json.load(f)

        pkgs = m_data.get("packages", [])
        if not args.json:
            print(f"\n[*] Reverting AppOps & Standby Buckets for {len(pkgs)} package(s)...")

        reset_results = []
        for item in pkgs:
            p = item["package"]
            orig_mode = "allow" if item.get("orig_appops") in ["allow", "default"] else item.get("orig_appops", "allow")
            orig_bucket = item.get("orig_bucket", "active")
            
            ok_op, msg_op = set_appops_restriction(p, mode=orig_mode, serial=target_serial, dry_run=args.dry_run)
            ok_b, msg_b = set_standby_bucket(p, bucket=orig_bucket, serial=target_serial, dry_run=args.dry_run)
            
            reset_results.append({
                "package": p,
                "appops_restored": ok_op,
                "bucket_restored": ok_b
            })
            if not args.json:
                print(f"  ✅ Reverted {p}: AppOps -> {orig_mode}, Bucket -> {orig_bucket}")

        if not args.dry_run:
            log_device_action(
                slug,
                "AppOps & Standby Reset Point Restored",
                f"Restored background execution permissions for {len(pkgs)} packages from manifest {os.path.basename(manifest_path)}.",
                {"manifest": manifest_path, "results": reset_results}
            )

        if args.json:
            print(json.dumps({"status": "reset_complete", "packages": reset_results}, indent=2))
        return

    # 2. Reset single app
    if args.reset_app:
        pkg = args.reset_app.strip()
        ok_op, msg_op = set_appops_restriction(pkg, mode="allow", serial=target_serial, dry_run=args.dry_run)
        ok_b, msg_b = set_standby_bucket(pkg, bucket="active", serial=target_serial, dry_run=args.dry_run)
        if args.json:
            print(json.dumps({"package": pkg, "appops": msg_op, "bucket": msg_b}, indent=2))
        else:
            print(f"✅ {msg_op}")
            print(f"✅ {msg_b}")
        return

    # 3. Determine target apps
    target_pkgs = []
    if args.app:
        target_pkgs.append(args.app.strip())
    elif args.preset == "social":
        ok, out = run_adb(["-s", target_serial, "shell", "pm list packages"])
        if ok and out:
            installed = set(l.replace("package:", "").strip() for l in out.splitlines())
            target_pkgs = [p for p in PRESET_BACKGROUND_HOGS if p in installed]
    elif args.preset == "all-user":
        ok, out = run_adb(["-s", target_serial, "shell", "pm list packages -3"])
        if ok and out:
            target_pkgs = [l.replace("package:", "").strip() for l in out.splitlines() if l.strip()]

    if not target_pkgs:
        print("ℹ️ No matching target packages found on device.")
        return

    if not args.json:
        mode_label = "[DRY-RUN] " if args.dry_run else ""
        print("\n" + "="*70)
        print(f" 🛡️ {mode_label}APPOPS & STANDBY BUCKET MANAGER: {info['brand'].upper()} {info['model']}")
        print("="*70)
        print(f"  • Mode        : AppOps {args.mode.upper()}")
        print(f"  • Bucket      : {args.bucket.upper()}")
        print(f"  • Target Apps : {len(target_pkgs)} package(s)")

    # 4. Snapshot original states for pre-flight reset point
    packages_state = []
    for p in target_pkgs:
        orig_op = get_appops_state(p, "RUN_IN_BACKGROUND", target_serial)
        orig_b = get_standby_bucket(p, target_serial)
        packages_state.append({
            "package": p,
            "orig_appops": orig_op,
            "orig_bucket": orig_b
        })

    manifest_file = ""
    if not args.dry_run:
        manifest_file = create_appops_manifest(target_serial, info, packages_state)
        if not args.json:
            print(f"  • Reset Point : backups/{os.path.basename(manifest_file)}")
            print("="*70 + "\n")

    # 5. Apply restrictions
    results = []
    applied_count = 0
    for item in packages_state:
        p = item["package"]
        ok_op, msg_op = set_appops_restriction(p, mode=args.mode, serial=target_serial, dry_run=args.dry_run)
        ok_b, msg_b = set_standby_bucket(p, bucket=args.bucket, serial=target_serial, dry_run=args.dry_run)
        success = ok_op and ok_b
        if success:
            applied_count += 1
        results.append({
            "package": p,
            "success": success,
            "appops_msg": msg_op,
            "bucket_msg": msg_b
        })
        if not args.json:
            icon = "✅" if success else "⚠️"
            print(f"{icon} {p}:")
            print(f"   • {msg_op}")
            print(f"   • {msg_b}")

    # Log in local device PC audit vault
    if not args.dry_run and applied_count > 0:
        log_device_action(
            slug,
            f"AppOps Background Limits & Standby Buckets ({args.mode})",
            f"Restricted background activity and set '{args.bucket}' standby bucket for {applied_count} app(s).",
            {
                "mode": args.mode,
                "bucket": args.bucket,
                "packages": [item["package"] for item in packages_state],
                "manifest_path": manifest_file,
                "reset_point": f"python scripts/appops_restrict.py --reset-manifest {os.path.basename(manifest_file)}"
            }
        )

    if args.json:
        print(json.dumps({
            "dry_run": args.dry_run,
            "mode": args.mode,
            "bucket": args.bucket,
            "processed": applied_count,
            "manifest": manifest_file,
            "results": results
        }, indent=2))
        return

    print("\n" + "="*70)
    print(f" ✅ Processed {applied_count} / {len(packages_state)} package(s).")
    if not args.dry_run and manifest_file:
        print(f" 🔄 Reset Point Saved: python scripts/appops_restrict.py --reset-manifest {os.path.basename(manifest_file)}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
