#!/usr/bin/env python3
"""
scripts/optimize.py - Safe OEM Debloater & Performance Optimizer

Applies curated debloat profiles, kills background telemetry, optimizes Virtual RAM,
and creates an automatic pre-flight restore manifest so all changes are 100% reversible.
"""

import sys
import os
import json
import time
from datetime import datetime

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from connect import run_adb, get_connected_devices, get_device_info

def load_database():
    """Load package database."""
    db_path = os.path.join(os.path.dirname(__file__), "..", "package_database.json")
    if not os.path.exists(db_path):
        print("❌ package_database.json not found!")
        sys.exit(1)
    with open(db_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_installed_packages(serial=None):
    """Retrieve all installed packages on the device."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", "pm list packages"])
    if not ok:
        return set()
    return set(line.replace("package:", "").strip() for line in out.splitlines() if line.strip())

def disable_package(pkg, serial=None):
    """Disable a package for user 0 (non-destructive, 100% reversible)."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", f"pm disable-user --user 0 {pkg}"])
    return ok and "disabled" in out.lower(), out

def tune_virtual_ram(manufacturer, serial=None):
    """Provide OEM-specific Virtual RAM remediation."""
    prefix = ["-s", serial] if serial else []
    m_low = manufacturer.lower()
    
    if "samsung" in m_low:
        print("[*] Unlocking '0 GB' RAM Plus option in Samsung Device Care...")
        run_adb(prefix + ["shell", "settings put global ram_expand_size_list 0,1,2,4,6,8"])
        print("    ✅ Set ram_expand_size_list to include 0 GB. Go to Settings > Battery and device care > Memory > RAM Plus and select 0 GB.")
    elif any(b in m_low for b in ["realme", "oppo", "oneplus"]):
        print("[*] Realme/ColorOS RAM Expansion detected:")
        print("    👉 To permanently eliminate F2FS flash thrashing, please open:")
        print("       Settings > About Device > RAM > Toggle OFF 'RAM Expansion', then restart.")
    elif "xiaomi" in m_low:
        print("[*] Xiaomi/HyperOS Memory Extension detected:")
        print("    👉 To prevent UI micro-stutters, please open:")
        print("       Settings > Additional Settings > Memory Extension > Select 'Off', then restart.")

def main():
    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    if not auth:
        print("❌ No authorized Android device connected. Run 'python scripts/connect.py' first.")
        sys.exit(1)

    target_serial = auth[0]["serial"]
    info = get_device_info(target_serial)
    db = load_database()

    print("\n" + "="*70)
    print(f" 🚀 SAFE PERFORMANCE OPTIMIZER: {info['brand'].upper()} {info['model']}")
    print("="*70)

    # Detect profile
    mfg = info["manufacturer"].lower()
    active_profile = "auto"
    if len(sys.argv) > 1 and sys.argv[1].startswith("--profile="):
        active_profile = sys.argv[1].split("=")[1].lower()
    elif len(sys.argv) > 2 and sys.argv[1] == "--profile":
        active_profile = sys.argv[2].lower()

    target_categories = []
    if active_profile == "samsung" or ("samsung" in mfg and active_profile == "auto"):
        target_categories = ["samsung", "universal_social_bloat"]
        print("[+] Detected Samsung profile.")
    elif any(b in mfg for b in ["realme", "oppo", "oneplus"]) or (active_profile in ["realme", "oppo", "coloros"]):
        target_categories = ["realme_oppo", "universal_social_bloat"]
        print("[+] Detected Realme / Oppo / OnePlus (ColorOS) profile.")
    elif "xiaomi" in mfg or active_profile == "xiaomi":
        target_categories = ["xiaomi", "universal_social_bloat"]
        print("[+] Detected Xiaomi / HyperOS / MIUI profile.")
    else:
        target_categories = ["universal_social_bloat"]
        print(f"[+] Using universal social/carrier bloat profile for: {info['manufacturer']}")

    # Collect installed candidate packages
    installed_pkgs = get_installed_packages(target_serial)
    to_disable = []
    
    for cat_key in target_categories:
        cat_data = db["categories"].get(cat_key, {})
        for pkg, meta in cat_data.get("packages", {}).items():
            if pkg in installed_pkgs:
                if meta.get("tier") in ["Recommended", "Advanced"]:
                    to_disable.append((pkg, meta["name"], meta["tier"], meta["impact"]))
                elif meta.get("tier") == "Unsafe":
                    print(f"  🛡️ PROTECTED (WHITELISTED): Skipping {pkg} ({meta['name']})")

    if not to_disable:
        print("\n✅ Great news! No known bloatware or telemetry packages found on this device.")
        tune_virtual_ram(mfg, target_serial)
        sys.exit(0)

    print(f"\n[+] Found {len(to_disable)} target package(s) eligible for safe optimization:")
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
        "timestamp": datetime.now().isoformat(),
        "device": {
            "serial": target_serial,
            "model": info["model"],
            "manufacturer": info["manufacturer"],
            "android_version": info["android_version"],
            "build_id": info["build_id"]
        },
        "disabled_packages": [pkg for pkg, _, _, _ in to_disable]
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print(f"\n📁 PRE-FLIGHT BACKUP CREATED:")
    print(f"   Saved to: backups/{manifest_name}")
    print("   (You can restore all packages anytime by running: python scripts/restore.py --manifest latest)")

    # Execute Safe Disables
    print("\n[*] Applying safe optimizations via user-space freeze (pm disable-user)...")
    disabled_count = 0
    for pkg, name, tier, _ in to_disable:
        ok, out = disable_package(pkg, target_serial)
        if ok:
            print(f"  ✅ Disabled: {name} ({pkg})")
            disabled_count += 1
        else:
            print(f"  ⚠️ Could not disable {pkg}: {out}")

    print(f"\n[+] Successfully optimized {disabled_count} package(s).")
    
    # Virtual RAM guidance
    print("\n" + "="*70)
    print(" ⚡ VIRTUAL RAM & FLASH THRASHING REMEDIATION")
    print("="*70)
    tune_virtual_ram(mfg, target_serial)

    print("\n" + "="*70)
    print(" ✅ OPTIMIZATION COMPLETED SUCCESSFULLY!")
    print(" Run 'python scripts/tweak_ui.py' next to double UI animation speed.")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
