#!/usr/bin/env python3
"""
scripts/connect.py - Device Connection & Authorization Wizard

Detects ADB, scans connected USB or wireless Android devices, guides users through
Developer Options, USB Debugging, and authorization popups, and extracts device metadata.
"""

import sys
import os
import re
import subprocess
import shutil

PACKAGE_REGEX = re.compile(r"^[a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)+$")

def validate_package_name(pkg: str) -> bool:
    """Validate package name against standard Android naming convention to prevent shell injection."""
    return bool(pkg and PACKAGE_REGEX.match(pkg.strip()))


if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def find_adb():
    """Locate adb binary in PATH or common Android SDK directories."""
    adb_path = shutil.which("adb")
    if adb_path:
        return adb_path
    
    # Common fallback locations on Windows
    fallbacks = [
        r"C:\platform-tools\adb.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
        r"C:\Program Files\Android\platform-tools\adb.exe"
    ]
    for p in fallbacks:
        if shutil.which(p):
            return p
    return None

def run_adb(args, timeout=10):
    """Safely execute an adb command with strict timeout and automatic target serial routing."""
    adb = find_adb()
    if not adb:
        return False, "ADB binary not found on this machine."

    final_args = list(args)
    target_serial = os.environ.get("ANDROID_SERIAL")
    if target_serial and "-s" not in final_args and len(final_args) > 0:
        first_cmd = final_args[0]
        if first_cmd not in ["devices", "connect", "pair", "kill-server", "start-server", "version"]:
            final_args = ["-s", target_serial] + final_args

    cmd = [adb] + final_args
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return res.returncode == 0, res.stdout.strip() if res.returncode == 0 else res.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout} seconds."
    except Exception as e:
        return False, str(e)

def get_connected_devices():
    """List devices and their status."""
    ok, out = run_adb(["devices", "-l"])
    if not ok:
        return []
    
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    devices = []
    for line in lines[1:]: # Skip 'List of devices attached'
        parts = line.split()
        if len(parts) >= 2:
            serial = parts[0]
            status = parts[1]
            extra = " ".join(parts[2:])
            devices.append({"serial": serial, "status": status, "extra": extra})
    return devices

def get_device_info(serial=None):
    """Retrieve OEM, model, and Android OS version."""
    prefix = ["-s", serial] if serial else []
    
    props = {
        "manufacturer": "ro.product.manufacturer",
        "model": "ro.product.model",
        "brand": "ro.product.brand",
        "android_version": "ro.build.version.release",
        "sdk_level": "ro.build.version.sdk",
        "build_id": "ro.build.display.id",
        "security_patch": "ro.build.version.security_patch"
    }
    
    info = {}
    for key, prop in props.items():
        ok, val = run_adb(prefix + ["shell", f"getprop {prop}"])
        info[key] = val if ok else "Unknown"
        
    return info

def show_connection_guide():
    """Display step-by-step instructions for user."""
    print("\n" + "="*70)
    print(" 📱 HOW TO CONNECT YOUR ANDROID PHONE (USB & WIRELESS GUIDE)")
    print("="*70)
    print("""
STEP 1: ENABLE DEVELOPER OPTIONS
  1. Open 'Settings' on your phone.
  2. Tap 'About Phone' (or 'About Device' > 'Version' on Realme/Oppo/Xiaomi).
  3. Find 'Build Number' and tap it rapidly 7 times.
  4. You will see: 'You are now a developer!'.

STEP 2: TURN ON USB DEBUGGING
  1. Go back to main 'Settings' > 'System' (or 'Additional Settings' / 'Developer Options').
  2. Open 'Developer Options'.
  3. Toggle ON: 'USB Debugging'.
  4. (For Xiaomi/Realme/Oppo): Also toggle ON 'Install via USB' and 'USB Debugging (Security settings)' if available.

STEP 3: CONNECT CABLE & AUTHORIZE
  1. Plug your phone into this PC using a USB data cable (ensure it supports data, not charging-only).
  2. Unlock your phone's screen.
  3. Look for a popup saying: 'Allow USB debugging?'.
  4. CHECK THE BOX: ☑ 'Always allow from this computer' and tap 'ALLOW' or 'OK'.

STEP 4 (OPTIONAL): WIRELESS DEBUGGING (Android 11+)
  If you prefer no USB cable:
  1. In 'Developer Options' on phone, turn on 'Wireless Debugging'.
  2. Tap 'Pair device with pairing code' to view IP, Port, and 6-digit Code.
  3. Run: python scripts/connect.py --pair <IP>:<PORT> <code>
  4. Then connect: python scripts/connect.py --connect <IP>:<PORT>
""")
    print("="*70 + "\n")

def main():
    adb = find_adb()
    if not adb:
        print("\n❌ ERROR: ADB is not installed or not in PATH.")
        print("Please install Android SDK Platform-Tools or ensure adb.exe is accessible.\n")
        sys.exit(1)

    # Handle Wireless pairing if flags passed
    if len(sys.argv) > 1:
        if sys.argv[1] == "--pair" and len(sys.argv) >= 4:
            ip_port = sys.argv[2]
            code = sys.argv[3]
            print(f"[*] Pairing with {ip_port} using code {code}...")
            ok, out = run_adb(["pair", ip_port, code])
            print(out)
            return
        elif sys.argv[1] == "--connect" and len(sys.argv) >= 3:
            ip_port = sys.argv[2]
            print(f"[*] Connecting to {ip_port}...")
            ok, out = run_adb(["connect", ip_port])
            print(out)
            return

    print(f"[*] ADB located: {adb}")
    print("[*] Scanning for connected Android devices...")
    
    devices = get_connected_devices()
    if not devices:
        print("\n⚠️ No Android devices detected.")
        show_connection_guide()
        sys.exit(0)

    print(f"\n[+] Found {len(devices)} device(s):")
    for idx, dev in enumerate(devices, 1):
        status_label = dev["status"]
        if status_label == "device":
            status_label = "✅ AUTHORIZED & READY"
        elif status_label == "unauthorized":
            status_label = "⚠️ UNAUTHORIZED (Check phone screen for permission prompt)"
        elif status_label == "offline":
            status_label = "❌ OFFLINE (Reconnect cable or toggle USB debugging)"
            
        print(f"  {idx}. Serial: {dev['serial']} | Status: {status_label}")

    # Inspect first authorized device
    authorized = [d for d in devices if d["status"] == "device"]
    if not authorized:
        print("\n⚠️ Device is connected but UNAUTHORIZED.")
        print("👉 Please unlock your phone screen, check 'Always allow from this computer', and tap OK.")
        sys.exit(0)

    target = authorized[0]
    print(f"\n[*] Probing target device: {target['serial']}...")
    info = get_device_info(target["serial"])
    
    print("\n" + "="*50)
    print(" 📱 TARGET DEVICE HARDWARE & OS SPECIFICATION")
    print("="*50)
    print(f"  • Manufacturer    : {info['manufacturer'].capitalize()}")
    print(f"  • Brand / Model   : {info['brand'].upper()} {info['model']}")
    print(f"  • Android Version : Android {info['android_version']} (SDK {info['sdk_level']})")
    print(f"  • Security Patch  : {info['security_patch']}")
    print(f"  • Build ID        : {info['build_id']}")
    print("="*50)
    print("\n✅ Device is fully authorized and ready for diagnostics and optimization!")

if __name__ == "__main__":
    main()
