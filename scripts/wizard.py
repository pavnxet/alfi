#!/usr/bin/env python3
"""
scripts/wizard.py - ALFi: Android Lag Fixer Interactive Control Dashboard

A sleek, cyber-grade terminal control dashboard and guided workflow engine for ALFi.
Connects multi-tier optimization (Low, Medium, High, Ultra), empirical battery proof,
deep Doze auditing, diagnostics, benchmarks, ART compilation, AppOps limits, emergency
rescue, and real-time screen mirroring into a clean, modern interface.
"""

import sys
import os
import shutil
import subprocess
import argparse
import json
from typing import Dict, Any, Optional, Tuple, List

# Ensure scripts directory is in sys.path
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Enable Windows Virtual Terminal Processing for ANSI colors
if os.name == "nt":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        hOut = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(hOut, ctypes.byref(mode))
        mode.value |= 0x0004  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        kernel32.SetConsoleMode(hOut, mode)
    except Exception:
        pass

from connect import run_adb, get_connected_devices, get_device_info
from device_tracker import get_device_fingerprint
from modes import (
    plan_mode_optimization,
    PRESET_BACKGROUND_HOGS,
    load_database,
    get_installed_packages,
    confirm_preflight_plan
)

# ANSI Palette (ALFi Brand: Neon Mint Green, Dark Charcoal, Lightning Yellow, Crisp White)
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_GREEN = "\033[1;38;2;0;230;118m"      # ALFi Neon Mint Green
C_GREEN_DIM = "\033[38;2;0;180;90m"
C_WHITE = "\033[1;38;2;255;255;255m"    # Crisp White
C_YELLOW = "\033[1;38;2;255;235;59m"    # Lightning Bolt Yellow
C_CYAN = "\033[1;38;2;0;229;255m"       # Electric Cyan
C_ORANGE = "\033[1;38;2;255;152;0m"     # High Mode Amber
C_RED = "\033[1;38;2;255;82;82m"        # Ultra Mode Crimson
C_GRAY = "\033[38;2;120;144;156m"       # Slate Gray
C_BORDER = "\033[38;2;55;71;79m"        # Dark Box Lines
C_CARD_BG = "\033[48;2;24;32;36m"

ACTIONS_MAP = {
    "modes": {
        "title": "Multi-Tier Optimization (Low / Medium / High / Ultra)",
        "script": "modes.py",
        "args": []
    },
    "diagnose": {
        "title": "Diagnose Root Causes (CPU, Memory Pressure, zRAM Swapping)",
        "script": "diagnose.py",
        "args": []
    },
    "bench": {
        "title": "Frame Pacing Benchmark (Jank Ratio & 1% Low FPS)",
        "script": "bench.py",
        "args": ["--app", "com.android.settings", "--duration", "8"]
    },
    "power": {
        "title": "BatteryStats & Wakelock Reduction Audit (Before vs After)",
        "script": "power_audit.py",
        "args": ["--audit"]
    },
    "doze": {
        "title": "Deep Doze Enforcement & DeviceIdle Whitelist Clean",
        "script": "doze_boost.py",
        "args": ["--audit"]
    },
    "compile": {
        "title": "Ahead-Of-Time (AOT) ART Pre-Compile (Kill Launch Stutter)",
        "script": "compile_speed.py",
        "args": ["--all-user-apps", "--filter", "speed-profile"]
    },
    "appops": {
        "title": "AppOps Background Limits (Throttle Social/Shopping Hogs)",
        "script": "appops_restrict.py",
        "args": ["--preset", "social", "--bucket", "restricted"]
    },
    "ui_speed": {
        "title": "Fast 0.5x UI Animations & System Cache Maintenance",
        "script": "tweak_ui.py",
        "args": ["--scale", "0.5"]
    },
    "shizuku": {
        "title": "Export Standalone On-Device Shizuku Scripts (.sh)",
        "script": "export_shizuku.py",
        "args": ["--profile", "all"]
    },
    "rescue": {
        "title": "Emergency Feature Rescue (Fix Critical Broken Services)",
        "script": "rescue.py",
        "args": ["--fix-critical"]
    },
    "restore": {
        "title": "1-Click Rollback / Restore From Latest Manifest",
        "script": "restore.py",
        "args": ["--manifest", "latest"]
    },
    "vault": {
        "title": "Multi-Device Hardware Audit Vault & History",
        "script": "device_tracker.py",
        "args": ["--status"]
    },
    "update_db": {
        "title": "Update Community Debloat Catalog (UAD-ng Ingestion)",
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

def clear_screen():
    """Clear terminal screen and wipe scrollback buffer for a smooth app-like redraw."""
    if os.environ.get("NO_COLOR"):
        return
    try:
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")
        sys.stdout.write("\033[H\033[2J\033[3J")
        sys.stdout.flush()
    except Exception:
        pass

def find_scrcpy_binary() -> Optional[str]:
    """Auto-detect scrcpy executable across system PATH and standard installation locations."""
    found = shutil.which("scrcpy")
    if found:
        return found

    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\scrcpy\scrcpy.exe"),
        r"C:\Program Files\scrcpy\scrcpy.exe",
        r"C:\scrcpy\scrcpy.exe",
        r"C:\Tools\scrcpy\scrcpy.exe",
        os.path.expanduser("~/scrcpy/scrcpy.exe"),
        "/usr/bin/scrcpy",
        "/usr/local/bin/scrcpy",
        "/opt/homebrew/bin/scrcpy"
    ]
    for c in candidates:
        if c and os.path.exists(c):
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
    extra_args: Optional[List[str]] = None,
    serial: Optional[str] = None
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

    env = dict(os.environ)
    if serial:
        env["ANDROID_SERIAL"] = serial

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env
        )
        if proc.returncode != 0:
            err_box = f"\n{C_RED}╭{'─' * 72}╮{C_RESET}\n"
            err_box += f"{C_RED}│ ⚠️  ACTION NOTIFICATION (Exit Code {proc.returncode}){' ' * 38}│{C_RESET}\n"
            err_box += f"{C_RED}╰{'─' * 72}╯{C_RESET}\n"
            err_box += proc.stdout
            return False, err_box
        return True, proc.stdout
    except Exception as e:
        err_box = f"\n{C_RED}╭{'─' * 72}╮{C_RESET}\n"
        err_box += f"{C_RED}│ ❌  EXECUTION FAILED: {str(e)[:50]:<48}│{C_RESET}\n"
        err_box += f"{C_RED}╰{'─' * 72}╯{C_RESET}\n"
        return False, err_box

def print_banner():
    """Print the ALFi ASCII brand logo and subtitle."""
    banner = f"""
{C_GREEN}   █████╗ ██╗     ███████╗██╗
  ██╔══██╗██║     ██╔════╝██║
  ███████║██║     █████╗  ██║
  ██╔══██║██║     ██╔══╝  ██║
  ██║  ██║███████╗██║     ██║
  ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝{C_RESET}
  {C_YELLOW}⚡{C_RESET} {C_WHITE}A L F i{C_RESET}  {C_GRAY}—{C_RESET}  {C_GREEN}A N D R O I D   L A G   F I X E R{C_RESET}  {C_GRAY}[v1.2.0]{C_RESET}  {C_YELLOW}⚡{C_RESET}
"""
    print(banner)

def print_device_card(
    device_info: Optional[Dict[str, Any]] = None,
    total_devices: int = 0,
    active_serial: Optional[str] = None
):
    """Render a modern rounded status card for connected hardware."""
    width = 74
    scrcpy_bin = find_scrcpy_binary()
    mirror_label = f"{C_GREEN}READY{C_RESET}" if scrcpy_bin else f"{C_GRAY}NOT FOUND{C_RESET}"

    print(f"{C_BORDER}╭{'─' * (width - 2)}╮{C_RESET}")
    if device_info and active_serial:
        brand = device_info.get("brand", "Unknown").upper()
        model = device_info.get("model", "Device")
        android = device_info.get("android_version", "?")
        sdk = device_info.get("sdk_level", "?")
        patch = device_info.get("security_patch", "N/A")
        is_wireless = ":" in active_serial
        conn_label = "WIRELESS" if is_wireless else "USB"

        line1 = f"  {C_GREEN}●{C_RESET} {C_WHITE}ACTIVE PHONE{C_RESET}  : {brand} {model} ({conn_label})"
        line2 = f"  {C_CYAN}●{C_RESET} {C_WHITE}PLATFORM{C_RESET}      : Android {android} (SDK {sdk})   {C_GRAY}● Patch: {patch}{C_RESET}"
        
        if total_devices > 1:
            line3 = f"  {C_YELLOW}●{C_RESET} {C_WHITE}TARGET STATUS{C_RESET} : ONLINE ({total_devices} attached)     {C_CYAN}● Switch: [D]{C_RESET}"
        else:
            line3 = f"  {C_GREEN}●{C_RESET} {C_WHITE}STATUS{C_RESET}        : ONLINE (ADB Authorized)   {C_GRAY}● Mirror: {mirror_label}{C_RESET}"

        print(f"{C_BORDER}│{C_RESET}{line1:<95}{C_BORDER}│{C_RESET}")
        print(f"{C_BORDER}│{C_RESET}{line2:<105}{C_BORDER}│{C_RESET}")
        print(f"{C_BORDER}│{C_RESET}{line3:<105}{C_BORDER}│{C_RESET}")
    elif total_devices > 0:
        line1 = f"  {C_YELLOW}⚠️  HARDWARE{C_RESET}     : {total_devices} DEVICE(S) DETECTED (UNAUTHORIZED)"
        line2 = f"  {C_WHITE}💡 ACTION NEEDED{C_RESET} : Unlock phone screen and tap 'Always allow from this computer'"
        line3 = f"  {C_GRAY}● STATUS{C_RESET}        : WAITING FOR RSA KEY       {C_CYAN}● Manage: [D]{C_RESET}"
        print(f"{C_BORDER}│{C_RESET}{line1:<95}{C_BORDER}│{C_RESET}")
        print(f"{C_BORDER}│{C_RESET}{line2:<95}{C_BORDER}│{C_RESET}")
        print(f"{C_BORDER}│{C_RESET}{line3:<105}{C_BORDER}│{C_RESET}")
    else:
        line1 = f"  {C_YELLOW}○{C_RESET} {C_WHITE}HARDWARE{C_RESET}      : NO PHYSICAL DEVICE CONNECTED (Simulator / Headless)"
        line2 = f"  {C_CYAN}💡 TIP{C_RESET}           : Plug in USB cable or connect via Wireless Debugging [D]"
        line3 = f"  {C_GRAY}●{C_RESET} {C_WHITE}STATUS{C_RESET}        : STANDBY                   {C_GRAY}● Mirror: {mirror_label}{C_RESET}"
        print(f"{C_BORDER}│{C_RESET}{line1:<84}{C_BORDER}│{C_RESET}")
        print(f"{C_BORDER}│{C_RESET}{line2:<84}{C_BORDER}│{C_RESET}")
        print(f"{C_BORDER}│{C_RESET}{line3:<105}{C_BORDER}│{C_RESET}")
    print(f"{C_BORDER}╰{'─' * (width - 2)}╯{C_RESET}")

def print_menu(total_devices: int = 0):
    """Display categorized command decks with rounded box formatting."""
    width = 74

    def print_deck(title: str, items: List[Tuple[str, str, str]]):
        header = f"─ {title} "
        border_top = f"{C_BORDER}╭{header}{'─' * (width - 2 - len(header))}╮{C_RESET}"
        print(border_top)
        for num, icon, desc in items:
            key_str = f"{C_GREEN}[{num.rjust(2)}]{C_RESET}"
            content = f"  {key_str} {icon}  {C_WHITE}{desc}{C_RESET}"
            print(f"{C_BORDER}│{C_RESET}{content:<90}{C_BORDER}│{C_RESET}")
        print(f"{C_BORDER}╰{'─' * (width - 2)}╯{C_RESET}")

    # Deck 1: Fast Track
    print_deck("⚡ FAST TRACK: MULTI-TIER TUNING", [
        (" 1", "🚀", "Multi-Tier Optimization (" + C_GREEN + "Low" + C_RESET + " | " + C_YELLOW + "Medium" + C_RESET + " | " + C_ORANGE + "High" + C_RESET + " | " + C_RED + "Ultra" + C_RESET + ")")
    ])

    # Deck 2: Diagnostics & Audit
    print_deck("🔍 DIAGNOSTICS & HARDWARE AUDIT", [
        (" 2", "🔍", "Diagnose Root Causes (CPU, Memory Pressure & zRAM Swapping)"),
        (" 3", "⏱️ ", "Run Frame Pacing Benchmark (Jank Ratio & 1% Low FPS)"),
        (" 4", "⚡", "BatteryStats & Wakelock Reduction Audit (Before vs After)"),
        (" 5", "🔋", "Deep Doze Enforcement & DeviceIdle Battery Allowlist Clean")
    ])

    # Deck 3: Engine Tuning
    print_deck("🚀 ENGINE TUNING & BACKGROUND RESTRAINTS", [
        (" 6", "⚡", "Ahead-Of-Time (AOT) ART Pre-Compile (Speed Up Launches)"),
        (" 7", "🛡️ ", "AppOps Background Limits (Throttle Social & Shopping Hogs)"),
        (" 8", "🎨", "Fast 0.5x UI Animations & System Cache Maintenance")
    ])

    # Deck 4: Defense & Rescue
    print_deck("🚑 DEFENSE, RESCUE & RECOVERY", [
        (" 9", "📱", "Export Standalone On-Device Shizuku Scripts (.sh)"),
        ("10", "🚑", "Emergency Feature Rescue (Fix Critical Broken Services)"),
        ("11", "🔄", "1-Click Rollback / Restore From Latest Snapshot Manifest"),
        ("12", "📊", "Multi-Device Hardware Audit Vault & History Records"),
        ("13", "🌐", "Update Community Debloat Catalog (UAD-ng Ingestion)")
    ])

    # Deck 5: System Control
    dev_tag = f" ({total_devices} Connected)" if total_devices > 1 else ""
    sys_items = [
        (" D", "📱", f"Device Manager & Switch Target Phone{dev_tag}")
    ]
    if find_scrcpy_binary():
        sys_items.append((" S", "🖥️ ", "Launch Real-Time Screen Mirroring (scrcpy)"))
    sys_items.append((" 0", "🚪", "Exit Dashboard"))
    print_deck("⚙️ SYSTEM CONTROL", sys_items)

def prompt_device_selection(
    current_serial: Optional[str] = None
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Interactive Device Manager and Target Switcher for ALFi."""
    import time
    while True:
        clear_screen()
        print_banner()
        width = 74

        print(f"{C_BORDER}╭{'─' * (width - 2)}╮{C_RESET}")
        title = f"{C_YELLOW}⚡{C_RESET} {C_WHITE}ALFi DEVICE MANAGER & TARGET SELECTOR{C_RESET} {C_YELLOW}⚡{C_RESET}"
        print(f"{C_BORDER}│{C_RESET}{title:^90}{C_BORDER}│{C_RESET}")
        print(f"{C_BORDER}╰{'─' * (width - 2)}╯{C_RESET}\n")

        devices = get_connected_devices()

        if not devices:
            print(f"  {C_YELLOW}○ NO PHYSICAL ANDROID DEVICES CURRENTLY DETECTED BY ADB{C_RESET}\n")
            print(f"  {C_WHITE}💡 Quick Connection Checklist:{C_RESET}")
            print(f"     1. {C_GRAY}Settings -> About Phone -> Tap 'Build Number' 7 times (Developer Options).{C_RESET}")
            print(f"     2. {C_GRAY}Settings -> System / Developer Options -> Toggle 'USB Debugging' ON.{C_RESET}")
            print(f"     3. {C_GRAY}Plug phone into PC via USB cable (or enable Wireless Debugging).{C_RESET}")
            print(f"     4. {C_GRAY}Unlock phone screen and check 'Always allow from this computer'.{C_RESET}\n")
        else:
            print(f"  {C_WHITE}Detected {len(devices)} device(s) attached via ADB:{C_RESET}\n")
            for idx, dev in enumerate(devices, 1):
                s = dev["serial"]
                status = dev["status"]
                is_wireless = (":" in s)
                conn_type = "Wireless Debugging" if is_wireless else "USB Cable"

                if status == "device":
                    info = get_device_info(s)
                    brand = info.get("brand", "Android").upper()
                    model = info.get("model", "Device")
                    os_ver = f"Android {info.get('android_version', '?')} (SDK {info.get('sdk_level', '?')})"

                    if s == current_serial:
                        tag = f"{C_GREEN}🟢 ACTIVE TARGET{C_RESET}"
                    else:
                        tag = f"{C_WHITE}⚪ AVAILABLE    {C_RESET}"

                    print(f"  {C_GREEN}[ {idx} ]{C_RESET} {tag} : {C_WHITE}{brand} {model}{C_RESET}")
                    print(f"        {C_GRAY}• Serial   :{C_RESET} {s} ({conn_type})")
                    print(f"        {C_GRAY}• Platform :{C_RESET} {os_ver}")
                    print(f"        {C_GRAY}• Status   :{C_RESET} {C_GREEN}Authorized & Ready{C_RESET}\n")
                elif status == "unauthorized":
                    print(f"  {C_YELLOW}[ {idx} ] ⚠️  PENDING       : {C_WHITE}{s}{C_RESET} ({conn_type})")
                    print(f"        {C_GRAY}• Status   :{C_RESET} {C_RED}UNAUTHORIZED (Check phone screen for RSA prompt!){C_RESET}\n")
                else:
                    print(f"  {C_GRAY}[ {idx} ] ❌ OFFLINE       : {s} ({status}){C_RESET}\n")

        print(f"  {C_CYAN}[ R ] 🔄 Refresh Device Scan{C_RESET}")
        print(f"  {C_CYAN}[ W ] 📶 Pair / Connect Wireless Phone (IP:Port + Pairing Code){C_RESET}")
        print(f"  {C_GRAY}[ 0 ] 🔙 Return to Dashboard{C_RESET}")
        print(f"{C_BORDER}{'─' * width}{C_RESET}")

        try:
            choice = input(f"\n{C_GREEN}👉 Select option or device number: {C_RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            return current_serial, (get_device_info(current_serial) if current_serial else None)

        if choice in ["0", "q", "exit", "back"]:
            return current_serial, (get_device_info(current_serial) if current_serial else None)

        if choice.upper() == "R":
            continue

        if choice.upper() == "W":
            print(f"\n{C_BORDER}{'─' * width}{C_RESET}")
            print(f"  {C_WHITE}📶 WIRELESS DEBUGGING SETUP (Android 11+){C_RESET}")
            print(f"  {C_GRAY}Go to Settings -> Developer Options -> Wireless Debugging on your phone.{C_RESET}")
            print(f"{C_BORDER}{'─' * width}{C_RESET}")
            try:
                ip_port = input(f"{C_GREEN}👉 Enter Phone IP & Port (e.g. 192.168.1.50:39845): {C_RESET}").strip()
                if not ip_port:
                    continue
                pair_code = input(f"{C_YELLOW}👉 Enter 6-digit Pairing Code (or press Enter if already paired): {C_RESET}").strip()
                if pair_code:
                    pair_port = input(f"{C_GREEN}👉 Enter Pairing Port (shown under 'Pair device with code'): {C_RESET}").strip()
                    pair_target = f"{ip_port.split(':')[0]}:{pair_port}" if pair_port else ip_port
                    print(f"[*] Pairing with {pair_target} using code {pair_code}...")
                    run_adb(["pair", pair_target, pair_code])
                print(f"[*] Connecting to {ip_port}...")
                ok, out = run_adb(["connect", ip_port])
                print(f"[*] Result: {out}")
                input(f"\n{C_GRAY}Press Enter to refresh devices...{C_RESET}")
                continue
            except (KeyboardInterrupt, EOFError):
                continue

        # Try selecting device by index
        try:
            dev_idx = int(choice) - 1
            if 0 <= dev_idx < len(devices):
                target_dev = devices[dev_idx]
                if target_dev["status"] != "device":
                    print(f"\n{C_RED}⚠️ Cannot select this device: Status is '{target_dev['status']}'.{C_RESET}")
                    if target_dev["status"] == "unauthorized":
                        print("👉 Please unlock your phone and tap 'Allow USB debugging' on the popup first.")
                    input(f"\n{C_GRAY}Press Enter to continue...{C_RESET}")
                    continue

                chosen_serial = target_dev["serial"]
                os.environ["ANDROID_SERIAL"] = chosen_serial
                info = get_device_info(chosen_serial)
                brand = info.get("brand", "Android").upper()
                model = info.get("model", "Device")
                print(f"\n{C_GREEN}✅ Active target switched to: {brand} {model} ({chosen_serial}){C_RESET}")
                time.sleep(1)
                return chosen_serial, info
            else:
                print(f"\n{C_RED}⚠️ Invalid device number.{C_RESET}")
                input(f"{C_GRAY}Press Enter to try again...{C_RESET}")
        except ValueError:
            print(f"\n{C_RED}⚠️ Invalid option. Enter device number, R, W, or 0.{C_RESET}")
            input(f"{C_GRAY}Press Enter to try again...{C_RESET}")

def prompt_mode_selection(dry_run: bool = False, serial: Optional[str] = None) -> Tuple[bool, str]:
    """Display modern ALFi 4-Tier Visual Selection Deck."""
    clear_screen()
    print_banner()
    width = 74
    print(f"\n{C_BORDER}╭{'─' * (width - 2)}╮{C_RESET}")
    title = f"{C_YELLOW}⚡{C_RESET} {C_WHITE}CHOOSE OPTIMIZATION ARCHITECTURE{C_RESET} {C_YELLOW}⚡{C_RESET}"
    print(f"{C_BORDER}│{C_RESET}{title:^90}{C_BORDER}│{C_RESET}")
    print(f"{C_BORDER}╰{'─' * (width - 2)}╯{C_RESET}\n")

    print(f"  {C_GREEN}[ 1 ] 🟢 LOW MODE{C_RESET} ─────── {C_WHITE}SAFE BASELINE (Zero Risk){C_RESET}")
    print(f"        {C_GRAY}• Scope   :{C_RESET} Carrier adware stubs, 0.75x animations, stale cache trim")
    print(f"        {C_GRAY}• Target  :{C_RESET} Family phones, work profiles, zero tolerance for feature changes\n")

    print(f"  {C_YELLOW}[ 2 ] 🟡 MEDIUM MODE{C_RESET} ──── {C_WHITE}BALANCED DAILY DRIVER (Recommended){C_RESET}")
    print(f"        {C_GRAY}• Scope   :{C_RESET} Low + OEM telemetry (Glance, Meta, MSA), 0.5x animations,")
    print(f"                    ART speed-profile on top user apps, social AppOps limits")
    print(f"        {C_GRAY}• Target  :{C_RESET} Everyday smartphones wanting snappy UI & cooler battery\n")

    print(f"  {C_ORANGE}[ 3 ] 🟠 HIGH MODE{C_RESET} ────── {C_WHITE}AGGRESSIVE ACCELERATION (Sluggish/Budget Devices){C_RESET}")
    print(f"        {C_GRAY}• Scope   :{C_RESET} Medium + vendor bloat (Bixby, Joyose), App Standby RESTRICTED,")
    print(f"                    Deep Doze allowlist cleanup, Virtual RAM off guidance")
    print(f"        {C_GRAY}• Target  :{C_RESET} Power users, older devices, budget 2GB-4GB hardware with lag\n")

    print(f"  {C_RED}[ 4 ] 🔴 ULTRA MODE{C_RESET} ───── {C_WHITE}EXTREME STRIP-DOWN (High-Risk / Power Users){C_RESET}")
    print(f"        {C_GRAY}• Scope   :{C_RESET} High + duplicate OEM accounts (Samsung/Mi ID), duplicate stores,")
    print(f"                    secondary keyboards/launchers, 0.0x zero animations, full AOT")
    print(f"        {C_GRAY}• Safety  :{C_RESET} {C_RED}Double-Gate: Dependency Graph Check + Requires 'I UNDERSTAND'{C_RESET}\n")

    print(f"  {C_GRAY}[ 0 ] 🔙 Return to Main Menu{C_RESET}")
    print(f"{C_BORDER}{'─' * width}{C_RESET}")

    try:
        choice = input(f"{C_GREEN}👉 Select mode [1-4]: {C_RESET}").strip()
    except (KeyboardInterrupt, EOFError):
        return False, "Aborted by user."

    if choice in ["0", "q", "exit", "back"]:
        return False, "Returned to Main Menu."

    mode_map = {"1": "low", "2": "medium", "3": "high", "4": "ultra"}
    if choice not in mode_map:
        return False, "Cancelled or invalid mode selection."

    selected_mode = mode_map[choice]

    # Fetch device state & formulate pre-flight action plan
    installed = get_installed_packages(serial=serial)
    device_info = get_device_info(serial) if serial else None
    if not device_info:
        device_info = {"brand": "Generic", "model": "Device", "android_version": "14", "sdk_level": "34"}
    manufacturer = device_info.get("brand", "generic")
    db = load_database()
    plan = plan_mode_optimization(selected_mode, installed, manufacturer=manufacturer, db=db)
    cfg = plan["config"]
    target_social = [p for p in PRESET_BACKGROUND_HOGS if p in installed] if cfg["appops_preset"] else []
    target_compile = [p for p in PRESET_BACKGROUND_HOGS if p in installed][:5] if cfg["art_filter"] else []

    # Display Pre-Flight Action Report & Confirmation Gate
    confirmed = confirm_preflight_plan(plan, device_info, target_social, target_compile)
    if not confirmed:
        return False, "Optimization cancelled by user. Zero changes were made to your device."

    extra_args = ["--mode", selected_mode, "--yes"]

    if selected_mode == "ultra":
        clear_screen()
        print_banner()
        print(f"\n{C_RED}{'!' * width}")
        print(" ⚠️ CAUTION: ULTRA MODE SELECTED (High-Risk System Strip-Down)")
        print(f"{'!' * width}{C_RESET}")
        print(" Ultra mode aggressively strips duplicate OEM stores, cloud sync accounts,")
        print(" secondary keyboards, and freezes background services completely.")
        print(f"{C_BORDER}{'─' * width}{C_RESET}")
        try:
            val = input(f"{C_YELLOW}👉 Type 'I UNDERSTAND' to confirm Ultra mode execution: {C_RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            return False, "Aborted by user."

        if val != "I UNDERSTAND":
            return False, "Safety Gate: 'I UNDERSTAND' was not entered. Ultra mode cancelled."
        extra_args.append("--force-ultra")

    return run_wizard_action("modes", dry_run=dry_run, extra_args=extra_args, serial=serial)

def main():
    parser = argparse.ArgumentParser(description="ALFi - Android Lag Fixer Control Wizard")
    parser.add_argument("--action", choices=list(ACTIONS_MAP.keys()), help="Execute a specific action non-interactively")
    parser.add_argument("--mode", choices=["low", "medium", "high", "ultra"], help="Target mode when running 'modes' action")
    parser.add_argument("--serial", "-s", help="Target specific device serial or IP:port")
    parser.add_argument("--dry-run", action="store_true", help="Simulate action without executing live ADB mutations")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON status")
    args = parser.parse_args()

    # Detect device
    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    active_serial = args.serial if args.serial else (auth[0]["serial"] if auth else None)
    if active_serial:
        os.environ["ANDROID_SERIAL"] = active_serial
    device_info = get_device_info(active_serial) if active_serial else None

    # Non-interactive CLI action
    if args.action:
        extra_args = []
        if args.action == "modes" and args.mode:
            extra_args = ["--mode", args.mode, "--yes"]
            if args.mode == "ultra":
                extra_args.append("--force-ultra")
        ok, output = run_wizard_action(args.action, dry_run=args.dry_run, extra_args=extra_args, serial=active_serial)
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

    # Interactive Dashboard Loop
    while True:
        # Dynamically refresh device inventory
        devices = get_connected_devices()
        auth = [d for d in devices if d["status"] == "device"]
        auth_serials = [d["serial"] for d in auth]

        # Auto-heal active serial if disconnected
        if active_serial and active_serial not in auth_serials:
            active_serial = auth[0]["serial"] if auth else None
            device_info = get_device_info(active_serial) if active_serial else None
            if active_serial:
                os.environ["ANDROID_SERIAL"] = active_serial
            elif "ANDROID_SERIAL" in os.environ:
                del os.environ["ANDROID_SERIAL"]
        elif not active_serial and auth:
            active_serial = auth[0]["serial"]
            os.environ["ANDROID_SERIAL"] = active_serial
            device_info = get_device_info(active_serial)

        clear_screen()
        print_banner()
        print_device_card(device_info, total_devices=len(devices), active_serial=active_serial)
        print_menu(total_devices=len(devices))

        try:
            choice = input(f"\n{C_GREEN}👉 Select an action [0-{len(MENU_ORDER)}]: {C_RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting ALFi.")
            break

        if choice in ["0", "exit", "quit", "q"]:
            print(f"\n{C_GREEN}⚡ Thanks for using ALFi! Goodbye! ⚡{C_RESET}\n")
            break

        if choice.upper() == "D":
            active_serial, device_info = prompt_device_selection(current_serial=active_serial)
            continue

        if choice.upper() == "S":
            ok, msg = launch_scrcpy(serial=active_serial)
            print(f"\n[*] {msg}\n")
            input(f"{C_GRAY}Press Enter to return to dashboard...{C_RESET}")
            continue

        selected_key = None
        for num, key in MENU_ORDER:
            if choice == num:
                selected_key = key
                break

        if not selected_key:
            print(f"\n{C_RED}⚠️ Invalid choice. Please enter a valid action number [0-{len(MENU_ORDER)}], D, or S.{C_RESET}\n")
            input(f"{C_GRAY}Press Enter to continue...{C_RESET}")
            continue

        if selected_key == "modes":
            ok, out = prompt_mode_selection(dry_run=args.dry_run, serial=active_serial)
            clear_screen()
            print_banner()
            print(f"\n{out}")
        else:
            clear_screen()
            print_banner()
            print(f"\n[*] Executing: {ACTIONS_MAP[selected_key]['title']}...\n")
            ok, out = run_wizard_action(selected_key, dry_run=args.dry_run, serial=active_serial)
            print(out)

        print(f"\n{C_BORDER}{'─' * 74}{C_RESET}")
        input(f"{C_GRAY}Press Enter to return to ALFi dashboard...{C_RESET}")

if __name__ == "__main__":
    main()
