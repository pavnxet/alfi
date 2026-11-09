#!/usr/bin/env python3
"""
scripts/wizard.py - Unified Interactive Terminal Control Wizard

An interactive terminal dashboard and guided workflow engine that connects all
diagnostic, benchmarking, debloating, compilation, AppOps restriction, emergency rescue,
and restoration tools into a clean, unified interface.
"""

import sys
import os
import subprocess
import argparse
import json
from typing import Dict, Any, Optional

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from connect import run_adb, get_connected_devices, get_device_info
from device_tracker import get_device_fingerprint

SCRIPTS_DIR = os.path.dirname(__file__)

ACTIONS_MAP = {
    "diagnose": {
        "title": "🔍 Diagnose Root Causes (CPU, Memory, Swapping)",
        "script": "diagnose.py",
        "args": []
    },
    "bench": {
        "title": "⏱️ Run Frame Pacing Benchmark (Jank Ratio & 1% Low FPS)",
        "script": "bench.py",
        "args": ["--app", "com.android.settings", "--duration", "8"]
    },
    "debloat": {
        "title": "🧹 Safe OEM Debloat (Disable Carrier & OEM Junk)",
        "script": "optimize.py",
        "args": ["--profile", "auto"]
    },
    "compile": {
        "title": "🚀 ART Ahead-Of-Time Pre-Compile (Speed Up Launch Stutter)",
        "script": "compile_speed.py",
        "args": ["--all-user-apps", "--filter", "speed-profile"]
    },
    "appops": {
        "title": "🛡️ AppOps Background Limits (Throttle Social/Shopping Hogs)",
        "script": "appops_restrict.py",
        "args": ["--preset", "social", "--bucket", "restricted"]
    },
    "ui_speed": {
        "title": "🎨 Fast 0.5x UI Animations & System Cache Trimming",
        "script": "tweak_ui.py",
        "args": ["--scale", "0.5", "--trim-cache"]
    },
    "shizuku": {
        "title": "📱 Export Standalone On-Device Shizuku Scripts",
        "script": "export_shizuku.py",
        "args": ["--profile", "all"]
    },
    "rescue": {
        "title": "🚑 Emergency Feature Rescue (Fix Critical Broken Services)",
        "script": "rescue.py",
        "args": ["--fix-critical"]
    },
    "restore": {
        "title": "🔄 1-Click Rollback / Restore From Latest Manifest",
        "script": "restore.py",
        "args": ["--manifest", "latest"]
    },
    "vault": {
        "title": "📊 Multi-Device Audit Vault & History",
        "script": "device_tracker.py",
        "args": ["--status"]
    },
    "update_db": {
        "title": "🌐 Update Community Debloat Package Database",
        "script": "update_database.py",
        "args": []
    }
}

MENU_ORDER = [
    ("1", "diagnose"),
    ("2", "bench"),
    ("3", "debloat"),
    ("4", "compile"),
    ("5", "appops"),
    ("6", "ui_speed"),
    ("7", "shizuku"),
    ("8", "rescue"),
    ("9", "restore"),
    ("10", "vault"),
    ("11", "update_db")
]

def run_wizard_action(
    action_key: str,
    dry_run: bool = False,
    extra_args: Optional[list] = None
) -> Tuple[bool, str]:
    """Execute a wizard action script as a subprocess."""
    if action_key not in ACTIONS_MAP:
        return False, f"Unknown action: {action_key}"

    entry = ACTIONS_MAP[action_key]
    script_path = os.path.join(SCRIPTS_DIR, entry["script"])
    cmd = [sys.executable, script_path] + entry["args"]
    if dry_run:
        cmd.append("--dry-run")
    if extra_args:
        cmd.extend(extra_args)

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        return proc.returncode == 0, proc.stdout
    except Exception as e:
        return False, str(e)

def print_header(device_info: Optional[Dict[str, Any]] = None):
    """Print standard dashboard header."""
    print("\n" + "="*70)
    print(" 🚀 ANDROID LAG FIXER & SECURITY OPTIMIZER - CONTROL DASHBOARD")
    print("="*70)
    if device_info:
        brand = device_info.get("brand", "Unknown").upper()
        model = device_info.get("model", "Device")
        android = device_info.get("android_version", "?")
        sdk = device_info.get("sdk_level", "?")
        print(f" 📱 Connected Device: {brand} {model} (Android {android}, SDK {sdk})")
    else:
        print(" ⚠️ No physical device connected (Interactive / Headless Mode)")
    print("="*70)

def print_menu():
    """Display interactive numbered menu."""
    for num, key in MENU_ORDER:
        title = ACTIONS_MAP[key]["title"]
        print(f"  [{num.rjust(2)}] {title}")
    print("  [ 0] 🚪 Exit Dashboard")
    print("="*70)

def main():
    parser = argparse.ArgumentParser(description="Unified Interactive Terminal Control Wizard")
    parser.add_argument("--action", choices=list(ACTIONS_MAP.keys()), help="Execute a specific action non-interactively")
    parser.add_argument("--dry-run", action="store_true", help="Simulate action without executing live ADB mutations")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON status")
    args = parser.parse_args()

    # Detect device
    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    device_info = get_device_info(auth[0]["serial"]) if auth else None

    # Non-interactive CLI action
    if args.action:
        ok, output = run_wizard_action(args.action, dry_run=args.dry_run)
        if args.json:
            print(json.dumps({
                "action": args.action,
                "success": ok,
                "dry_run": args.dry_run,
                "output": output
            }, indent=2))
        else:
            print(output)
        sys.exit(0 if ok else 1)

    # Interactive mode
    print_header(device_info)
    if not auth:
        print("💡 Hint: Connect your phone via USB or Wireless Debugging to unlock all actions.")

    while True:
        print_menu()
        try:
            choice = input("\n👉 Select an action [0-11]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting dashboard.")
            break

        if choice in ["0", "exit", "quit", "q"]:
            print("\n👋 Goodbye!")
            break

        selected_key = None
        for num, key in MENU_ORDER:
            if choice == num:
                selected_key = key
                break

        if not selected_key:
            print("⚠️ Invalid choice. Please enter a number between 0 and 11.\n")
            continue

        print(f"\n[*] Executing: {ACTIONS_MAP[selected_key]['title']}...\n")
        ok, out = run_wizard_action(selected_key, dry_run=args.dry_run)
        print(out)
        print("\n" + "-"*70)

if __name__ == "__main__":
    main()
