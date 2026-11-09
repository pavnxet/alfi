#!/usr/bin/env python3
"""
scripts/compile_speed.py - ART (Android Runtime) AOT Pre-Compilation & Reset Engine

Forces Ahead-of-Time (AOT) compilation of application bytecode into native machine code.
Eliminates JIT compilation stutter during launches and scrolling.
Includes automated pre-flight reset manifests to allow 1-click reversal if storage is constrained.
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

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from connect import run_adb, get_connected_devices, get_device_info, validate_package_name
from device_tracker import get_device_fingerprint, log_device_action

VALID_FILTERS = ["speed", "speed-profile", "everything", "verify"]

def get_package_compile_status(pkg: str, serial: Optional[str] = None) -> str:
    """Retrieve the current compilation filter/status of a package."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", f"dumpsys package {pkg}"])
    if not ok or not out:
        return "unknown"
    
    for line in out.splitlines():
        line_str = line.strip()
        if "compileReason=" in line_str or "status=" in line_str:
            return line_str
    return "default (JIT / uncompiled)"

def compile_package(
    pkg: str,
    compile_filter: str = "speed-profile",
    serial: Optional[str] = None,
    dry_run: bool = False,
    filter_type: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Compile a package using ART AOT compiler.
    Returns (success: bool, message: str)
    """
    if filter_type:
        compile_filter = filter_type

    if not validate_package_name(pkg):
        return False, f"Invalid package name format: '{pkg}'"
    
    if compile_filter not in VALID_FILTERS:
        return False, f"Invalid compilation filter: '{compile_filter}'. Must be one of {VALID_FILTERS}"

    prefix = ["-s", serial] if serial else []
    cmd = f"cmd package compile -m {compile_filter} -f {pkg}"
    
    if dry_run:
        return True, f"[DRY-RUN] Would execute: adb shell {cmd}"

    ok, out = run_adb(prefix + ["shell", cmd], timeout=90)
    if ok and "success" in out.lower():
        return True, f"Compiled {pkg} with filter '{compile_filter}'"
    return False, f"Compilation failed for {pkg}: {out}"

def reset_package_compilation(
    pkg: str,
    serial: Optional[str] = None,
    dry_run: bool = False
) -> Tuple[bool, str]:
    """
    Reset an application's compilation status back to default system state.
    """
    if not validate_package_name(pkg):
        return False, f"Invalid package name format: '{pkg}'"

    prefix = ["-s", serial] if serial else []
    cmd = f"cmd package compile --reset {pkg}"

    if dry_run:
        return True, f"[DRY-RUN] Would execute: adb shell {cmd}"

    ok, out = run_adb(prefix + ["shell", cmd], timeout=30)
    if ok and "success" in out.lower():
        return True, f"Reset compilation for {pkg} (reverted to default JIT state)"
    return False, f"Failed to reset {pkg}: {out}"

def create_compile_manifest(
    target_serial: str,
    device_info: Dict[str, Any],
    packages: List[str],
    compile_filter: str
) -> str:
    """Save an automated reset point manifest before compilation."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_model = device_info.get("model", "unknown").replace(" ", "_")
    manifest_name = f"compile_manifest_{safe_model}_{timestamp}.json"
    manifest_dir = os.path.join(os.path.dirname(__file__), "..", "backups")
    os.makedirs(manifest_dir, exist_ok=True)
    manifest_path = os.path.join(manifest_dir, manifest_name)

    data = {
        "timestamp": datetime.now().isoformat(),
        "type": "art_compilation_reset_point",
        "device": {
            "serial": target_serial,
            "model": device_info.get("model"),
            "manufacturer": device_info.get("manufacturer"),
            "android_version": device_info.get("android_version"),
            "build_id": device_info.get("build_id")
        },
        "compile_filter": compile_filter,
        "packages": packages,
        "reset_command": f"python scripts/compile_speed.py --reset-manifest {manifest_name}"
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return manifest_path

def main():
    parser = argparse.ArgumentParser(description="ART AOT Ahead-of-Time Pre-Compilation & Reset Tool")
    parser.add_argument("--app", help="Target package name to compile (e.g. com.android.settings)")
    parser.add_argument("--filter", default="speed-profile", choices=VALID_FILTERS, help="Compilation filter (default: speed-profile)")
    parser.add_argument("--all-user-apps", action="store_true", help="Compile all installed third-party user applications")
    parser.add_argument("--reset-app", help="Reset a specific package back to default uncompiled JIT state")
    parser.add_argument("--reset-manifest", help="Reset all packages from a compilation manifest file")
    parser.add_argument("--targets", action="store_true",
                        help="Compile only the apps still at status=verify (measured, not guessed)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate compilation commands without modifying device")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    if not auth and not args.dry_run:
        print("\n" + "="*70)
        print(" 🚀 ART AOT PRE-COMPILATION ENGINE [STANDALONE / SIMULATOR MODE]")
        print("="*70)
        print(" 💡 Connect your phone with USB Debugging enabled to execute live compilation.")
        args.dry_run = True

    target_serial = auth[0]["serial"] if auth else None
    info = get_device_info(target_serial) if target_serial else {"brand": "Generic", "model": "Android Device (Simulated)"}
    slug = "generic_simulator"
    if target_serial:
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
            print(f"\n[*] Resetting ART compilation for {len(pkgs)} package(s) from manifest...")

        reset_results = []
        for p in pkgs:
            ok, msg = reset_package_compilation(p, target_serial, dry_run=args.dry_run)
            reset_results.append({"pkg": p, "success": ok, "message": msg})
            if not args.json:
                icon = "✅" if ok else "⚠️"
                print(f"  {icon} {msg}")

        # Log reset in local device vault
        if not args.dry_run:
            log_device_action(
                slug,
                "ART Compilation Reset Point Restored",
                f"Reverted {len(pkgs)} packages to default JIT state from manifest {os.path.basename(manifest_path)}.",
                {"manifest": manifest_path, "results": reset_results}
            )

        if args.json:
            print(json.dumps({"status": "reset_complete", "packages": reset_results}, indent=2))
        return

    # 1b. Compile only the apps that are still interpreted
    if args.targets:
        import attrib as attrib_mod

        data = attrib_mod.collect(target_serial)
        if "error" in data:
            print("❌ Could not read dexopt state: %s" % data["error"])
            sys.exit(1)
        targets = sorted(p for p, meta in (data.get("dexopt", {}).get("packages") or {}).items()
                         if meta.get("status") == "verify")
        if not targets:
            print("✅ Nothing to do: no packages are stuck at status=verify.")
            return
        if args.json:
            print(json.dumps({"targets": targets, "dry_run": args.dry_run}, indent=2))
            if args.dry_run:
                return
        else:
            print("\n[*] %d package(s) still interpreted (status=verify):" % len(targets))
            for p in targets[:15]:
                print("    - " + p)
            if len(targets) > 15:
                print("    (+%d more)" % (len(targets) - 15))

        results = []
        for pkg in targets:
            ok, msg = compile_package(pkg, args.filter, target_serial, dry_run=args.dry_run)
            results.append({"package": pkg, "success": ok, "message": msg})
            if not args.json:
                print("  %s %s" % ("✅" if ok else "⚠️", msg))
        if not args.json:
            done = sum(1 for r in results if r["success"])
            print("\n✅ Compiled %d / %d target(s) with filter '%s'." % (done, len(results), args.filter))
        return

    # 2. Reset single app
    if args.reset_app:
        pkg = args.reset_app.strip()
        ok, msg = reset_package_compilation(pkg, target_serial, dry_run=args.dry_run)
        if args.json:
            print(json.dumps({"package": pkg, "success": ok, "message": msg}, indent=2))
        else:
            icon = "✅" if ok else "❌"
            print(f"{icon} {msg}")
        return

    # 3. Determine target packages to compile
    targets = []
    if args.app:
        targets.append(args.app.strip())
    elif target_serial and args.all_user_apps:
        ok, out = run_adb(["-s", target_serial, "shell", "pm list packages -3"])
        if ok and out:
            targets = [l.replace("package:", "").strip() for l in out.splitlines() if l.strip()]
    elif target_serial:
        candidates = ["com.android.settings", "com.google.android.googlequicksearchbox"]
        ok, out = run_adb(["-s", target_serial, "shell", "pm list packages"])
        if ok and out:
            inst = set(l.replace("package:", "").strip() for l in out.splitlines())
            targets = [c for c in candidates if c in inst]
        if not targets:
            targets = ["com.android.settings"]
    else:
        # Simulated target apps when offline
        targets = ["com.android.settings", "com.google.android.youtube"]

    if not targets:
        print("ℹ️ No target packages identified for compilation.")
        return

    if not args.json:
        mode_label = "[DRY-RUN] " if args.dry_run else ""
        print("\n" + "="*70)
        print(f" 🚀 {mode_label}ART AOT PRE-COMPILATION ENGINE: {info['brand'].upper()} {info['model']}")
        print("="*70)
        print(f"  • Filter Mode   : {args.filter}")
        print(f"  • Target Apps   : {len(targets)} package(s)")
        print(f"  • Device Slug   : {slug}")

    # Create pre-flight reset manifest
    manifest_file = ""
    if not args.dry_run:
        manifest_file = create_compile_manifest(target_serial, info, targets, args.filter)
        if not args.json:
            print(f"  • Reset Point   : backups/{os.path.basename(manifest_file)}")
            print("="*70)

    compile_results = []
    success_count = 0
    for p in targets:
        if not args.json:
            print(f"[*] Compiling {p} ({args.filter})...")
        ok, msg = compile_package(p, compile_filter=args.filter, serial=target_serial, dry_run=args.dry_run)
        compile_results.append({"pkg": p, "success": ok, "message": msg})
        if ok:
            success_count += 1
            if not args.json:
                print(f"  ✅ {msg}")
        else:
            if not args.json:
                print(f"  ⚠️ {msg}")

    # Record in local device PC audit vault
    if not args.dry_run and success_count > 0:
        log_device_action(
            slug,
            f"ART Ahead-Of-Time Compilation ({args.filter})",
            f"Pre-compiled {success_count} app(s) to eliminate JIT compilation stutter and app launch delay.",
            {
                "filter": args.filter,
                "packages": targets,
                "manifest_path": manifest_file,
                "reset_point": f"python scripts/compile_speed.py --reset-manifest {os.path.basename(manifest_file)}"
            }
        )

    if args.json:
        print(json.dumps({
            "dry_run": args.dry_run,
            "filter": args.filter,
            "compiled_count": success_count,
            "total": len(targets),
            "manifest": manifest_file,
            "results": compile_results
        }, indent=2))
        return

    print("\n" + "="*70)
    print(f" ✅ Successfully processed {success_count} / {len(targets)} package(s).")
    if not args.dry_run and manifest_file:
        print(f" 🔄 Reset Point Saved: python scripts/compile_speed.py --reset-manifest {os.path.basename(manifest_file)}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
