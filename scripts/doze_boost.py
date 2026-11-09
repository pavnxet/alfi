#!/usr/bin/env python3
"""
scripts/doze_boost.py - Deep Doze Enforcement & DeviceIdle Allowlist Auditor

Inspiration: Android DeviceIdle Subsystem & Brevent
Audits the system Doze allowlist (apps exempted from battery optimization),
strips third-party analytics and bloatware pollers from background battery exemptions,
and enforces rapid Deep Doze state transitions on screen-off.
Includes snapshot backup manifests for 1-click restoration.
"""

import sys
import os
import re
import json
import argparse
from datetime import datetime
from typing import Dict, Any, List, Set, Tuple, Optional

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from connect import run_adb, get_connected_devices, get_device_info, validate_package_name

# Essential system packages that must never be removed from the Doze whitelist
DOZE_SYSTEM_ALLOWLIST: Set[str] = {
    "com.android.phone",
    "com.android.systemui",
    "com.google.android.gms",
    "com.android.providers.telephony",
    "com.android.dialer",
    "com.google.android.dialer",
    "com.android.emergency"
}

# Known tracking/bloat packages that frequently abuse battery exemption
BLOAT_ALLOWLIST_CANDIDATES: Set[str] = {
    "com.facebook.katana",
    "com.facebook.services",
    "com.facebook.appmanager",
    "com.instagram.android",
    "com.snapchat.android",
    "com.eterno",
    "com.amazon.mShop.android.shopping",
    "com.flipkart.android",
    "com.myntra.android",
    "com.truecaller",
    "com.aura.oobe.samsung",
    "com.ironsource.aura.oobe",
    "com.miui.msa.global",
    "com.miui.analytics",
    "com.oplus.statistics.rom",
    "com.heytap.mcs"
}

def parse_deviceidle_whitelist(raw_output: str) -> Dict[str, List[str]]:
    """
    Parse dumpsys deviceidle whitelist output into structured lists.
    Returns: {"system": [...], "user": [...], "all": [...]}
    """
    system_whitelist: List[str] = []
    user_whitelist: List[str] = []
    all_packages: List[str] = []

    current_section = "system"
    for line in raw_output.splitlines():
        line = line.strip()
        if not line:
            continue
        if "User whitelist" in line or "User-whitelisted" in line:
            current_section = "user"
            continue
        if "System whitelist" in line or "System-whitelisted" in line:
            current_section = "system"
            continue

        # Detect line-level prefix or section headers (e.g. 'user,com.example.app,1001')
        line_lower = line.lower()
        line_type = None
        if line_lower.startswith("user,") or line_lower.startswith("user:"):
            line_type = "user"
        elif line_lower.startswith("system,") or line_lower.startswith("system:"):
            line_type = "system"

        effective_section = line_type if line_type else current_section

        # Output format can be 'system,com.example.app,1001' or 'com.example.app'
        parts = [p.strip() for p in line.split(",") if p.strip()]
        for p in parts:
            if re.match(r"^[a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)+$", p):
                all_packages.append(p)
                if effective_section == "user":
                    user_whitelist.append(p)
                else:
                    system_whitelist.append(p)

    return {
        "system": sorted(list(set(system_whitelist))),
        "user": sorted(list(set(user_whitelist))),
        "all": sorted(list(set(all_packages)))
    }

def get_current_whitelist(serial: Optional[str] = None) -> Dict[str, List[str]]:
    """Query dumpsys deviceidle whitelist from connected device."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", "dumpsys deviceidle whitelist"])
    if not ok or not out:
        return {"system": [], "user": [], "all": []}
    return parse_deviceidle_whitelist(out)

def create_doze_snapshot(
    whitelist_data: Dict[str, List[str]],
    serial: Optional[str] = None,
    tag: str = "pre_clean"
) -> str:
    """Save current Doze whitelist snapshot into backups/ directory."""
    backups_dir = os.path.join(os.path.dirname(__file__), "..", "backups")
    os.makedirs(backups_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest_name = f"doze_manifest_{tag}_{timestamp}.json"
    manifest_path = os.path.join(backups_dir, manifest_name)

    device_info = get_device_info(serial) if serial else {"brand": "Generic", "model": "Android"}

    manifest = {
        "manifest_version": "1.0.0",
        "type": "deviceidle_whitelist_backup",
        "timestamp": timestamp,
        "device": device_info,
        "whitelist": whitelist_data
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest_path

def remove_from_whitelist(
    package_name: str,
    serial: Optional[str] = None,
    dry_run: bool = False
) -> Tuple[bool, str]:
    """Remove a package from the deviceidle battery optimization whitelist."""
    if not validate_package_name(package_name):
        return False, f"Invalid package name: '{package_name}'"

    if package_name in DOZE_SYSTEM_ALLOWLIST:
        return False, f"Refused: '{package_name}' is a critical phone subsystem."

    prefix = ["-s", serial] if serial else []
    cmd = f"cmd deviceidle whitelist -{package_name}"

    if dry_run:
        return True, f"[DRY-RUN] Would execute: adb shell {cmd}"

    ok, out = run_adb(prefix + ["shell", cmd])
    if ok:
        return True, f"Removed '{package_name}' from Doze exemption whitelist."
    return False, f"Failed removing '{package_name}': {out}"

def add_to_whitelist(
    package_name: str,
    serial: Optional[str] = None,
    dry_run: bool = False
) -> Tuple[bool, str]:
    """Restore a package to the deviceidle battery optimization whitelist."""
    if not validate_package_name(package_name):
        return False, f"Invalid package name: '{package_name}'"

    prefix = ["-s", serial] if serial else []
    cmd = f"cmd deviceidle whitelist +{package_name}"

    if dry_run:
        return True, f"[DRY-RUN] Would execute: adb shell {cmd}"

    ok, out = run_adb(prefix + ["shell", cmd])
    if ok:
        return True, f"Added '{package_name}' to Doze exemption whitelist."
    return False, f"Failed adding '{package_name}': {out}"

def force_idle_state(serial: Optional[str] = None, dry_run: bool = False) -> Tuple[bool, str]:
    """Enforce immediate Deep Doze state transition (Inspiration: DeviceIdle force-idle)."""
    prefix = ["-s", serial] if serial else []
    if dry_run:
        return True, "[DRY-RUN] Would execute: adb shell cmd deviceidle force-idle"

    ok, out = run_adb(prefix + ["shell", "cmd deviceidle force-idle"])
    if ok:
        return True, "Enforced deviceidle force-idle state."
    # Fallback to step if force-idle is unsupported on older Android
    ok_step, out_step = run_adb(prefix + ["shell", "dumpsys deviceidle step"])
    if ok_step:
        return True, f"Stepped deviceidle state: {out_step.strip()}"
    return False, f"Failed enforcing idle state: {out}"

def audit_and_clean_whitelist(
    serial: Optional[str] = None,
    clean: bool = False,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Audit Doze whitelist and optionally clean rogue battery hogs."""
    whitelist_data = get_current_whitelist(serial=serial)
    all_whitelisted = whitelist_data.get("all", [])

    culprits = [p for p in all_whitelisted if p in BLOAT_ALLOWLIST_CANDIDATES]

    results: Dict[str, Any] = {
        "total_whitelisted": len(all_whitelisted),
        "system_count": len(whitelist_data.get("system", [])),
        "user_count": len(whitelist_data.get("user", [])),
        "culprits_found": culprits,
        "removed": [],
        "failed": [],
        "manifest_path": None
    }

    if clean and culprits:
        manifest_path = create_doze_snapshot(whitelist_data, serial=serial)
        results["manifest_path"] = manifest_path

        for pkg in culprits:
            ok, msg = remove_from_whitelist(pkg, serial=serial, dry_run=dry_run)
            if ok:
                results["removed"].append(pkg)
            else:
                results["failed"].append({"package": pkg, "error": msg})

    return results

def restore_doze_manifest(manifest_path: str, serial: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Restore Doze whitelist states from a backup manifest."""
    if not os.path.exists(manifest_path):
        return {"success": False, "error": f"Manifest not found: {manifest_path}"}

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    packages = data.get("whitelist", {}).get("user", [])
    restored: List[str] = []
    failed: List[Dict[str, str]] = []

    for pkg in packages:
        ok, msg = add_to_whitelist(pkg, serial=serial, dry_run=dry_run)
        if ok:
            restored.append(pkg)
        else:
            failed.append({"package": pkg, "error": msg})

    return {
        "success": len(failed) == 0,
        "restored": restored,
        "failed": failed
    }

def main():
    parser = argparse.ArgumentParser(description="Deep Doze Enforcement & DeviceIdle Allowlist Auditor")
    parser.add_argument("--audit", action="store_true", help="Inspect current Doze exemption allowlist")
    parser.add_argument("--clean", action="store_true", help="Remove third-party bloat from Doze exemption allowlist")
    parser.add_argument("--force-idle", action="store_true", help="Trigger immediate Deep Doze state transition")
    parser.add_argument("--restore", type=str, help="Restore whitelist exemptions from a manifest JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Simulate commands without executing live ADB mutations")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON status")
    args = parser.parse_args()

    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    serial = auth[0]["serial"] if auth else None

    if args.restore:
        res = restore_doze_manifest(args.restore, serial=serial, dry_run=args.dry_run)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"[*] Restored {len(res.get('restored', []))} packages to whitelist.")
        sys.exit(0 if res.get("success", False) else 1)

    if args.force_idle:
        ok, msg = force_idle_state(serial=serial, dry_run=args.dry_run)
        print(f"[*] Force-Idle: {msg}")
        sys.exit(0 if ok else 1)

    res = audit_and_clean_whitelist(serial=serial, clean=args.clean, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print("\n" + "=" * 65)
        print(" 🔋 DEVICEIDLE & DEEP DOZE ALLOWLIST AUDIT")
        print("=" * 65)
        print(f" Total Whitelisted Apps: {res['total_whitelisted']}")
        print(f" System Whitelist:       {res['system_count']}")
        print(f" User Whitelist:         {res['user_count']}")
        print(f" Rogue Culprits Found:   {len(res['culprits_found'])}")
        for c in res['culprits_found']:
            print(f"   ⚠️ {c}")

        if args.clean:
            print(f"\n[*] Cleaned {len(res['removed'])} rogue exemptions (Dry-Run: {args.dry_run}).")
            if res.get("manifest_path"):
                print(f"[*] Snapshot manifest saved to: {res['manifest_path']}")
        else:
            print("\n💡 Run with '--clean' to strip these apps from background battery exemption.")
        print("=" * 65 + "\n")

if __name__ == "__main__":
    main()
