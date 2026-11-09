#!/usr/bin/env python3
"""
scripts/wizard.py - Unified Interactive Terminal Control Wizard

An interactive terminal dashboard and guided workflow engine that connects all
multi-tier optimization modes (Low, Medium, High, Ultra), battery proofs, deep Doze,
diagnostics, benchmarking, compilation, AppOps restriction, emergency rescue,
restoration, and real-time screen mirroring into a clean, unified interface.
"""

import sys
import os
import shutil
import subprocess
import argparse
import json
from typing import Dict, Any, Optional, Tuple, List

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from connect import run_adb, get_connected_devices, get_device_info
from device_tracker import get_device_fingerprint

ACTIONS_MAP = {
    "modes": {
        "title": "🚀 Multi-Tier Optimization (Low / Medium / High / Ultra)",
        "script": "modes.py",
        "args": []
    },
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
    "power": {
        "title": "⚡ Empirical Battery & Wakelock Proof (Before vs After)",
        "script": "power_audit.py",
        "args": ["--audit"]
    },
    "doze": {
        "title": "🔋 Deep Doze Enforcement & DeviceIdle Allowlist Audit",
        "script": "doze_boost.py",
        "args": ["--audit"]
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
        "args": ["--scale", "0.5"]
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
    ("1", "modes"),
    ("2", "diagnose"),
    ("3", "bench"),
    ("4", "power"),
    ("5", "doze"),
    ("6", "compile"),
    ("7", "appops"),
    ("8", "ui_speed"),
    ("9", "shizuku"),
    ("10", "rescue"),
    ("11", "restore"),
    ("12", "vault"),
    ("13", "update_db")
]

def find_scrcpy_binary() -> Optional[str]:
    """Auto-detect scrcpy executable across system PATH and common installation paths."""
    # 1. System PATH
    found = shutil.which("scrcpy")
    if found:
        return found

    # 2. Common Windows download & tool directories
    candidates = [
        r"E:\Download\scrcpy-release-v3.2\scrcpy-win64-v3.2\scrcpy.exe",
        r"E:\Download\scrcpy-win64-v3.2\scrcpy.exe",
        r"C:\scrcpy\scrcpy.exe",
        r"C:\Tools\scrcpy\scrcpy.exe"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def launch_scrcpy(serial: Optional[str] = None) -> Tuple[bool, str]:
    """Launch scrcpy screen mirroring in a lightweight non-blocking process."""
    bin_path = find_scrcpy_binary()
    if not bin_path:
        return False, "scrcpy binary not found. Please install scrcpy or place it in your PATH."

    cmd = [bin_path, "--stay-awake", "--video-bit-rate=4M", "--max-size=1080"]
    if serial:
        cmd.extend(["-s", serial])

    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, f"Launched real-time screen mirror via: {bin_path}"
    except Exception as e:
        return False, f"Failed launching scrcpy: {e}"

def run_wizard_action(
    action_key: str,
    dry_run: bool = False,
    extra_args: Optional[List[str]] = None
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
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        return proc.returncode == 0, proc.stdout
    except Exception as e:
        return False, str(e)

def prompt_mode_selection(dry_run: bool = False) -> Tuple[bool, str]:
    """Prompt user interactively to pick among the 4 optimization modes."""
    print("\n" + "=" * 70)
    print(" 🚀 CHOOSE OPTIMIZATION MODE")
    print("=" * 70)
    print("  [1] 🟢 Low:    Carrier Stubs & Adware / 0.75x Animations / Zero Risk")
    print("  [2] 🟡 Medium: Balanced Daily Driver / Telemetry / 0.5x / Recommended")
    print("  [3] 🟠 High:   Aggressive / Vendor Bloat / Restricted Standby / 0 GB zRAM")
    print("  [4] 🔴 Ultra:  High-Risk / Strip Accounts & Duplicate Stores / 0.0x Animations")
    print("  [0] 🔙 Back to Main Menu")
    print("=" * 70)

    try:
        choice = input("👉 Select mode [1-4]: ").strip()
    except (KeyboardInterrupt, EOFError):
        return False, "Aborted by user."

    mode_map = {"1": "low", "2": "medium", "3": "high", "4": "ultra"}
    if choice not in mode_map:
        return False, "Cancelled or invalid mode selection."

    selected_mode = mode_map[choice]

    extra_args = ["--mode", selected_mode]

    if selected_mode == "ultra":
        print("\n" + "!" * 70)
        print(" ⚠️ CAUTION: ULTRA MODE SELECTED")
        print("!" * 70)
        print(" Ultra mode aggressively strips duplicate OEM stores, cloud accounts,")
        print(" secondary keyboards/launchers, and sets animations to 0.0x.")
        print("=" * 70)
        try:
            val = input(" 👉 Type 'I UNDERSTAND' to proceed: ").strip()
        except (KeyboardInterrupt, EOFError):
            return False, "Aborted by user."

        if val != "I UNDERSTAND":
            return False, "Safety Gate: 'I UNDERSTAND' was not entered. Ultra mode cancelled."
        extra_args.append("--force-ultra")

    return run_wizard_action("modes", dry_run=dry_run, extra_args=extra_args)

def print_header(device_info: Optional[Dict[str, Any]] = None):
    """Print standard dashboard header."""
    print("\n" + "=" * 70)
    print(" 🚀 ANDROID LAG FIXER & SECURITY OPTIMIZER - CONTROL DASHBOARD")
    print("=" * 70)
    if device_info:
        brand = device_info.get("brand", "Unknown").upper()
        model = device_info.get("model", "Device")
        android = device_info.get("android_version", "?")
        sdk = device_info.get("sdk_level", "?")
        print(f" 📱 Connected Device: {brand} {model} (Android {android}, SDK {sdk})")
    else:
        print(" ⚠️ No physical device connected (Interactive / Headless Mode)")

    scrcpy_bin = find_scrcpy_binary()
    if scrcpy_bin:
        print(f" 📱 Screen Mirroring: scrcpy detected ({os.path.basename(scrcpy_bin)})")
    print("=" * 70)

def print_menu():
    """Display interactive numbered menu."""
    for num, key in MENU_ORDER:
        title = ACTIONS_MAP[key]["title"]
        print(f"  [{num.rjust(2)}] {title}")

    scrcpy_bin = find_scrcpy_binary()
    if scrcpy_bin:
        print("  [ S] 📱 Launch Real-Time Screen Mirror (scrcpy)")

    print("  [ 0] 🚪 Exit Dashboard")
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description="Unified Interactive Terminal Control Wizard")
    parser.add_argument("--action", choices=list(ACTIONS_MAP.keys()), help="Execute a specific action non-interactively")
    parser.add_argument("--mode", choices=["low", "medium", "high", "ultra"], help="Target mode when running 'modes' action")
    parser.add_argument("--dry-run", action="store_true", help="Simulate action without executing live ADB mutations")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON status")
    args = parser.parse_args()

    # Detect device
    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    serial = auth[0]["serial"] if auth else None
    device_info = get_device_info(serial) if serial else None

    # Non-interactive CLI action
    if args.action:
        extra_args = []
        if args.action == "modes" and args.mode:
            extra_args = ["--mode", args.mode]
            if args.mode == "ultra":
                extra_args.append("--force-ultra")
        ok, output = run_wizard_action(args.action, dry_run=args.dry_run, extra_args=extra_args)
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
            choice = input(f"\n👉 Select an action [0-{len(MENU_ORDER)}]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting dashboard.")
            break

        if choice in ["0", "exit", "quit", "q"]:
            print("\n👋 Goodbye!")
            break

        if choice.upper() == "S":
            ok, msg = launch_scrcpy(serial=serial)
            print(f"\n[*] {msg}\n")
            continue

        selected_key = None
        for num, key in MENU_ORDER:
            if choice == num:
                selected_key = key
                break

        if not selected_key:
            print(f"⚠️ Invalid choice. Please enter a number between 0 and {len(MENU_ORDER)}.\n")
            continue

        if selected_key == "modes":
            ok, out = prompt_mode_selection(dry_run=args.dry_run)
            print(out)
        else:
            print(f"\n[*] Executing: {ACTIONS_MAP[selected_key]['title']}...\n")
            ok, out = run_wizard_action(selected_key, dry_run=args.dry_run)
            print(out)

        print("\n" + "-" * 70)

if __name__ == "__main__":
    main()
