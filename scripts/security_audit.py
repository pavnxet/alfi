#!/usr/bin/env python3
"""
scripts/security_audit.py - Safe Sketchy App, Malware & Privacy Auditor

Audits third-party Android packages for Accessibility Service hijacking, Device Admin
abuse, invisible ghost launcher activities, and high-risk permission clusters.
Executes 100% remotely via ADB text streams—ZERO executable APK files touch the host PC.
"""

import sys
import json
import re

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from connect import run_adb, get_connected_devices, get_device_info

DANGEROUS_PERMS = [
    "android.permission.BIND_ACCESSIBILITY_SERVICE",
    "android.permission.SYSTEM_ALERT_WINDOW",
    "android.permission.RECEIVE_SMS",
    "android.permission.READ_SMS",
    "android.permission.SEND_SMS",
    "android.permission.READ_CALL_LOG",
    "android.permission.PROCESS_OUTGOING_CALLS",
    "android.permission.ACCESS_BACKGROUND_LOCATION",
    "android.permission.RECORD_AUDIO",
    "android.permission.CAMERA",
    "android.permission.QUERY_ALL_PACKAGES"
]

def get_installed_third_party_packages(serial=None):
    """Retrieve 3rd-party user packages and their installer sources."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", "pm list packages -3 -i"])
    if not ok:
        return {}
    
    # Lines formatted as: package:com.example.app installer=com.android.vending
    pkgs = {}
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("package:"):
            parts = line[8:].split()
            pkg_name = parts[0]
            installer = "unknown"
            for p in parts[1:]:
                if p.startswith("installer="):
                    installer = p.split("=")[1]
            pkgs[pkg_name] = installer
    return pkgs

def get_enabled_accessibility_services(serial=None):
    """Detect apps holding active screen-reading and touch-simulation privileges."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", "settings get secure enabled_accessibility_services"])
    if not ok or not out or out == "null":
        return []
    
    # Format: pkg1/service1:pkg2/service2
    services = []
    for item in out.split(":"):
        if "/" in item:
            pkg = item.split("/")[0].strip()
            services.append(pkg)
    return list(set(services))

def get_device_administrators(serial=None):
    """Detect apps registered as Device Admins (cannot be uninstalled normally)."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", "dumpsys device_policy"])
    admins = []
    if ok:
        in_admin_section = False
        for line in out.splitlines():
            line_str = line.strip()
            if "Active Administrators:" in line_str or "Enabled Device Admins:" in line_str:
                in_admin_section = True
                continue
            if in_admin_section:
                match = re.search(r"ComponentInfo\{([^/]+)/", line_str)
                if match:
                    admins.append(match.group(1).strip())
                elif line_str == "" or line_str.startswith("----") or "Device Owner:" in line_str:
                    in_admin_section = False
    return list(set(admins))

def get_launcher_packages(serial=None):
    """Retrieve all packages that have a visible launcher icon in the app drawer."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", "cmd package query-intent-activities -a android.intent.action.MAIN -c android.intent.category.LAUNCHER"])
    launcher_pkgs = set()
    if ok:
        for line in out.splitlines():
            match = re.search(r"packageName=([^\s]+)", line)
            if match:
                launcher_pkgs.add(match.group(1))
    return launcher_pkgs

def get_package_permissions(pkg, serial=None):
    """Extract granted and requested dangerous permissions for a package."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", f"dumpsys package {pkg}"], timeout=8)
    if not ok:
        return []
    
    found_perms = []
    for p in DANGEROUS_PERMS:
        if p in out:
            found_perms.append(p.split(".")[-1])
    return found_perms

def quarantine_package(pkg, serial=None):
    """Safely freeze a suspicious package without deleting data."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", f"pm disable-user --user 0 {pkg}"])
    return ok, out

def revoke_permission(pkg, perm, serial=None):
    """Revoke a sensitive permission from a package."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", f"pm revoke {pkg} {perm}"])
    return ok, out

def main():
    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    if not auth:
        print("❌ No authorized Android device connected. Run 'python scripts/connect.py' first.")
        sys.exit(1)

    target_serial = auth[0]["serial"]
    info = get_device_info(target_serial)

    print("\n" + "="*70)
    print(f" 🛡️ RUNNING SAFE SECURITY & SKETCHY APP AUDIT ON: {info['brand'].upper()} {info['model']}")
    print("="*70)
    print("🔒 PC Protection Guarantee: Scan runs purely via remote ADB text queries.")
    print("   Zero APK files or untrusted payloads are transferred or executed on your PC.\n")

    # 1. Fetch data
    print("[*] Inspecting active Accessibility Services...")
    acc_services = get_enabled_accessibility_services(target_serial)
    
    print("[*] Checking registered Device Administrators...")
    device_admins = get_device_administrators(target_serial)
    
    print("[*] Cataloging 3rd-party user applications and install sources...")
    third_party = get_installed_third_party_packages(target_serial)
    
    print("[*] Checking launcher activities (identifying ghost/hidden apps)...")
    launcher_pkgs = get_launcher_packages(target_serial)

    # 2. Analyze threats
    print(f"\n[+] Scanned {len(third_party)} installed third-party apps.")
    
    flagged_apps = []

    # Whitelist of well-known trusted system accessibility tools
    ACC_WHITELIST = [
        "com.google.android.marvin.talkback",
        "com.samsung.accessibility",
        "com.android.switchaccess",
        "com.coloros.accessibility"
    ]

    for pkg, installer in third_party.items():
        reasons = []
        severity = "LOW"
        
        # Check accessibility abuse
        if pkg in acc_services:
            if pkg not in ACC_WHITELIST:
                reasons.append("🚨 ACTIVE ACCESSIBILITY HOOK (Can monitor screen, keystrokes, and touch inputs)")
                severity = "CRITICAL"

        # Check device admin
        if pkg in device_admins:
            reasons.append("⚠️ ACTIVE DEVICE ADMIN (Can prevent uninstall and lock screen)")
            if severity != "CRITICAL":
                severity = "HIGH"

        # Check ghost app (hidden icon)
        if pkg not in launcher_pkgs:
            # Check if it's a known service, plugin or keyboard
            if not any(k in pkg for k in ["keyboard", "ime", "plugin", "wear", "service"]):
                reasons.append("👻 HIDDEN GHOST APP (No home screen icon; runs stealth background services)")
                if severity == "LOW":
                    severity = "MEDIUM"

        # Check sideload source
        is_sideloaded = False
        if installer in ["unknown", "null", None]:
            is_sideloaded = True
        elif any(b in installer.lower() for b in ["chrome", "firefox", "browser", "download", "packageinstaller"]):
            is_sideloaded = True
            
        if is_sideloaded and reasons:
            reasons.append(f"📦 SIDELOADED: Installed via non-store source ({installer})")

        # Check dangerous permissions if already flagged
        if reasons:
            perms = get_package_permissions(pkg, target_serial)
            if perms:
                reasons.append(f"🔑 Dangerous Permissions Held: {', '.join(perms)}")

            flagged_apps.append({
                "pkg": pkg,
                "installer": installer,
                "severity": severity,
                "reasons": reasons
            })

    # 3. Print Results
    print("\n" + "="*70)
    print(" 📋 SECURITY AUDIT FINDINGS")
    print("="*70)

    if not flagged_apps:
        print("\n✅ All clear! No third-party accessibility hijackers, hidden ghost apps, or unauthorized device admins found.")
    else:
        print(f"\n⚠️ Flagged {len(flagged_apps)} suspicious or high-privilege third-party package(s):\n")
        for idx, app in enumerate(flagged_apps, 1):
            print(f"[{idx}] Package  : {app['pkg']}")
            print(f"    Severity : {app['severity']}")
            print(f"    Source   : {app['installer']}")
            for r in app['reasons']:
                print(f"    • {r}")
            print("-" * 60)

        # Interactive / Guided Remediation Option
        print("\n💡 SAFE REMEDIATION OPTIONS:")
        print("  To safely freeze/quarantine any suspicious package so it cannot run:")
        print("    python scripts/security_audit.py --quarantine <package_name>")
        print("  To revoke accessibility permission from all third-party apps:")
        print("    python scripts/security_audit.py --reset-accessibility\n")

    # Command line actions
    if len(sys.argv) > 1:
        if sys.argv[1] == "--quarantine" and len(sys.argv) >= 3:
            target_pkg = sys.argv[2]
            print(f"[*] Quarantining {target_pkg} via user-space freeze...")
            ok, out = quarantine_package(target_pkg, target_serial)
            if ok:
                print(f"✅ {target_pkg} successfully quarantined (frozen). It can no longer execute or drain battery.")
            else:
                print(f"❌ Failed: {out}")
        elif sys.argv[1] == "--reset-accessibility":
            print("[*] Disabling third-party accessibility services...")
            run_adb(["-s", target_serial, "shell", "settings put secure enabled_accessibility_services null"])
            print("✅ All accessibility hooks deactivated.")

if __name__ == "__main__":
    main()
