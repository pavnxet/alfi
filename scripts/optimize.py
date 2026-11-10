#!/usr/bin/env python3
"""
scripts/optimize.py - Safe OEM Debloater & Performance Optimizer

Applies curated debloat profiles, kills background telemetry, optimizes Virtual RAM,
and creates an automatic pre-flight restore manifest with verified state rollback.
"""

import sys
import os
import json
import argparse
import urllib.request
from datetime import datetime
from typing import Dict, Any

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from connect import run_adb, get_connected_devices, get_device_info
from operations import apply_package_state

UAD_LIST_URL = "https://raw.githubusercontent.com/Universal-Debloater-Alliance/universal-android-debloater-next-generation/main/resources/assets/uad_lists.json"

def get_database_path() -> str:
    """Resolve location of package_database.json across source repository and wheel installations."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "package_database.json"),
        os.path.join(here, "..", "package_database.json")
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.normpath(c)
    return os.path.normpath(os.path.join(here, "..", "package_database.json"))

def load_database() -> Dict[str, Any]:
    """Load package database."""
    db_path = get_database_path()
    if not os.path.exists(db_path):
        print("❌ package_database.json not found!")
        sys.exit(1)
    with open(db_path, "r", encoding="utf-8") as f:
        return json.load(f)

def update_database_from_upstream():
    """Fetch and merge upstream UAD-ng community debloat definitions."""
    db_path = get_database_path()
    print(f"[*] Fetching latest community package definitions from:\n    {UAD_LIST_URL}")
    try:
        req = urllib.request.Request(UAD_LIST_URL, headers={"User-Agent": "android-lag-fixer/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        current_db = load_database()
        from update_database import parse_community_list, merge_databases
        categorized, accepted, _ = parse_community_list(data)
        updated_db, new_count, mod_count = merge_databases(current_db, categorized)

        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(updated_db, f, indent=2)

        print(f"✅ Successfully merged {new_count} new packages and updated {mod_count} definitions into package_database.json!")
    except Exception as e:
        print(f"❌ Failed to fetch upstream package definitions: {e}")

def get_installed_packages(user_id: int = 0, serial=None):
    """Retrieve all installed packages on the device for target user."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", f"pm list packages --user {user_id}"])
    if not ok:
        return set()
    return set(line.replace("package:", "").strip() for line in out.splitlines() if line.strip())

def tune_virtual_ram(manufacturer: str, serial=None, dry_run: bool = False):
    """
    Provide OEM-specific Virtual RAM remediation.
    Correct technical explanation: Eliminates high zRAM CPU compression/decompression overhead
    on weak CPU cores during memory pressure, reducing dropped frames.
    """
    prefix = ["-s", serial] if serial else []
    m_low = manufacturer.lower()
    
    if "samsung" in m_low:
        if dry_run:
            print("    [DRY-RUN] Would run: settings put global ram_expand_size_list 0,1,2,4,6,8")
        else:
            print("[*] Unlocking '0 GB' RAM Plus option in Samsung Device Care...")
            run_adb(prefix + ["shell", "settings put global ram_expand_size_list 0,1,2,4,6,8"])
            print("    ✅ Set ram_expand_size_list to include 0 GB. Go to Settings > Battery and device care > Memory > RAM Plus and select 0 GB.")
    elif any(b in m_low for b in ["realme", "oppo", "oneplus"]):
        print("[*] Realme/ColorOS RAM Expansion detected:")
        print("    👉 To prevent zRAM compression CPU throttling, please open:")
        print("       Settings > About Device > RAM > Toggle OFF 'RAM Expansion', then restart.")
    elif "xiaomi" in m_low:
        print("[*] Xiaomi/HyperOS Memory Extension detected:")
        print("    👉 To eliminate jank and reduce zRAM CPU compression spikes, please open:")
        print("       Settings > Additional Settings > Memory Extension > Select 'Off', then restart.")

def main():
    parser = argparse.ArgumentParser(description="Safe OEM Debloater & Performance Optimizer")
    parser.add_argument("--profile", default="auto", help="Debloat profile: auto, samsung, xiaomi, realme, google, universal")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without modifying device state")
    parser.add_argument("--user", type=int, default=0, help="Android user profile ID (default: 0)")
    parser.add_argument("--update-db", action="store_true", help="Fetch latest community package lists from UAD-ng")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    if args.update_db:
        update_database_from_upstream()
        return

    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    if not auth:
        print("❌ No authorized Android device connected. Run 'python scripts/connect.py' first.")
        sys.exit(1)

    target_serial = auth[0]["serial"]
    info = get_device_info(target_serial)
    raw_sdk = info.get("sdk_level", 31)
    sdk_level = int(raw_sdk) if raw_sdk and str(raw_sdk).isdigit() else 31
    db = load_database()

    if not args.json:
        print("\n" + "="*70)
        mode_label = "[DRY-RUN PREVIEW] " if args.dry_run else ""
        print(f" 🚀 {mode_label}PERFORMANCE OPTIMIZER: {info['brand'].upper()} {info['model']} (User {args.user})")
        print("="*70)

    # Detect profile
    mfg = info["manufacturer"].lower()
    active_profile = args.profile.lower()

    target_categories = []
    if active_profile == "samsung" or ("samsung" in mfg and active_profile == "auto"):
        target_categories = ["samsung", "universal_social_bloat"]
        if not args.json:
            print("[+] Detected Samsung profile.")
    elif any(b in mfg for b in ["realme", "oppo", "oneplus"]) or (active_profile in ["realme", "oppo", "coloros"]):
        target_categories = ["realme_oppo", "universal_social_bloat"]
        if not args.json:
            print("[+] Detected Realme / Oppo / OnePlus (ColorOS) profile.")
    elif "xiaomi" in mfg or active_profile == "xiaomi":
        target_categories = ["xiaomi", "universal_social_bloat"]
        if not args.json:
            print("[+] Detected Xiaomi / HyperOS / MIUI profile.")
    else:
        target_categories = ["universal_social_bloat"]
        if not args.json:
            print(f"[+] Using universal social/carrier bloat profile for: {info['manufacturer']}")

    # Collect candidate packages
    installed_pkgs = get_installed_packages(user_id=args.user, serial=target_serial)
    to_disable = []
    
    for cat_key in target_categories:
        cat_data = db["categories"].get(cat_key, {})
        for pkg, meta in cat_data.get("packages", {}).items():
            if pkg in installed_pkgs:
                if meta.get("tier") in ["Recommended", "Advanced"]:
                    to_disable.append((pkg, meta["name"], meta["tier"], meta["impact"]))
                elif meta.get("tier") == "Unsafe" and not args.json:
                    print(f"  🛡️ PROTECTED (ALLOWLIST): Skipping critical package {pkg} ({meta['name']})")

    if not to_disable:
        if args.json:
            print(json.dumps({"status": "clean", "message": "No known bloatware found."}))
        else:
            print("\n✅ Great news! No known bloatware or telemetry packages found on this device.")
            tune_virtual_ram(mfg, target_serial, dry_run=args.dry_run)
        return

    if not args.json:
        print(f"\n[+] Found {len(to_disable)} target package(s) eligible for optimization:")
        for pkg, name, tier, impact in to_disable:
            print(f"  • [{tier}] {name} ({pkg})")
            print(f"    Impact: {impact}")

    # Generate Pre-flight Restore Manifest
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest_name = f"restore_manifest_{info['model']}_{timestamp}.json"
    manifest_dir = os.path.join(os.path.dirname(__file__), "..", "backups")
    os.makedirs(manifest_dir, exist_ok=True)
    manifest_path = os.path.join(manifest_dir, manifest_name)

    manifest_data = {
        "tool": "ALFi (Android Lag Fixer)",
        "repository": "https://github.com/pavnxet/alfi",
        "author": "pavnxet",
        "timestamp": datetime.now().isoformat(),
        "device": {
            "serial": target_serial,
            "model": info["model"],
            "manufacturer": info["manufacturer"],
            "android_version": info["android_version"],
            "sdk_level": sdk_level,
            "build_id": info["build_id"],
            "user_id": args.user
        },
        "disabled_packages": [pkg for pkg, _, _, _ in to_disable]
    }

    if not args.dry_run:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
        if not args.json:
            print(f"\n📁 PRE-FLIGHT BACKUP CREATED:")
            print(f"   Saved to: backups/{manifest_name}")
            print("   (Restore anytime: python scripts/restore.py --manifest latest)")

    # Execute Safe Disables via verified state machine
    if not args.json:
        print(f"\n[*] Applying optimizations via verified state machine (User {args.user})...")
    
    results = []
    disabled_count = 0
    for pkg, name, tier, _ in to_disable:
        ok, msg = apply_package_state(
            pkg=pkg,
            want="disabled",
            user_id=args.user,
            serial=target_serial,
            sdk_level=sdk_level,
            dry_run=args.dry_run
        )
        results.append({"pkg": pkg, "name": name, "success": ok, "message": msg})
        if ok:
            disabled_count += 1
            if not args.json:
                print(f"  ✅ {msg}")
        else:
            if not args.json:
                print(f"  ⚠️ {msg}")

    if args.json:
        print(json.dumps({
            "dry_run": args.dry_run,
            "device": info["model"],
            "optimized_count": disabled_count,
            "results": results
        }, indent=2))
        return

    print(f"\n[+] Successfully processed {disabled_count} / {len(to_disable)} package(s).")
    
    print("\n" + "="*70)
    print(" ⚡ VIRTUAL RAM & ZRAM MEMORY PRESSURE TUNING")
    print("="*70)
    tune_virtual_ram(mfg, target_serial, dry_run=args.dry_run)

    print("\n" + "="*70)
    print(" ✅ OPTIMIZATION COMPLETED SUCCESSFULLY!")
    print(" Run 'python scripts/bench.py' to measure exact UI framerate gains.")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
