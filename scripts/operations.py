#!/usr/bin/env python3
"""
scripts/operations.py - Resilient Android Package Mutation & State Verification Engine

Implements version-aware command resolution (Android 6 to 17+), UAD-style fallback
ladders (uninstall <-> disable), and post-mutation state verification to catch
silent exit-code-0 failures on HyperOS, One UI, and modern AOSP.
"""

import sys
import re
from typing import Tuple, Optional

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from connect import run_adb, validate_package_name

STATE_RE = re.compile(r"new state:\s*(\w[\w-]*)", re.IGNORECASE)

def get_package_state(pkg: str, user_id: int = 0, serial: Optional[str] = None) -> str:
    """
    Query the real package state for a specific user:
    Returns one of: 'enabled', 'disabled', 'uninstalled', 'not_found'
    """
    if not validate_package_name(pkg):
        return "invalid"
        
    prefix = ["-s", serial] if serial else []
    
    # 1. Quick check via dumpsys package
    ok, out = run_adb(prefix + ["shell", f"dumpsys package {pkg} | grep -m1 'enabled='"])
    if ok and out:
        # e.g.: enabled=0 (default), enabled=1 (enabled), enabled=2 (disabled), enabled=3 (disabled-user)
        if "enabled=2" in out or "enabled=3" in out or "disabled" in out.lower():
            return "disabled"
        if "enabled=1" in out or "enabled=0" in out:
            return "enabled"

    # 2. Comprehensive check via pm list packages
    ok_dis, dis_out = run_adb(prefix + ["shell", f"pm list packages -d --user {user_id} {pkg}"])
    if ok_dis and f"package:{pkg}" in dis_out.split():
        return "disabled"

    ok_en, en_out = run_adb(prefix + ["shell", f"pm list packages -e --user {user_id} {pkg}"])
    if ok_en and f"package:{pkg}" in en_out.split():
        return "enabled"

    # Check if package exists at all on the device (uninstalled for user 0)
    ok_all, all_out = run_adb(prefix + ["shell", f"pm list packages -u {pkg}"])
    if ok_all and f"package:{pkg}" in all_out.split():
        return "uninstalled"

    return "not_found"

def apply_package_state(
    pkg: str,
    want: str,
    user_id: int = 0,
    serial: Optional[str] = None,
    sdk_level: int = 31,
    dry_run: bool = False
) -> Tuple[bool, str]:
    """
    Safely transition package to desired state:
    want in {"disabled", "uninstalled", "enabled"}
    
    Returns (success: bool, status_message: str)
    """
    if not validate_package_name(pkg):
        return False, f"Invalid package name format: '{pkg}'"

    prefix = ["-s", serial] if serial else []
    want = want.lower().strip()

    # Android 17 (SDK 37+) compatibility check
    if want == "uninstalled" and sdk_level >= 37:
        print(f"  ℹ️ Android 17+ (SDK {sdk_level}) hard-blocks user-space system uninstall. Falling back to 'disable-user'.")
        want = "disabled"

    current = get_package_state(pkg, user_id, serial)
    if current == want:
        return True, f"Package {pkg} is already in state '{want}'"

    if dry_run:
        cmd_preview = f"pm disable-user --user {user_id} {pkg}" if want == "disabled" else (
            f"pm uninstall --user {user_id} {pkg}" if want == "uninstalled" else
            f"pm enable --user {user_id} {pkg}"
        )
        return True, f"[DRY-RUN] Would execute: adb shell {cmd_preview}"

    # Execution ladder
    if want == "disabled":
        # Primary command: pm disable-user
        ok, out = run_adb(prefix + ["shell", f"pm disable-user --user {user_id} {pkg}"])
        
        # Check for HyperOS / OEM SecurityException: 'Cannot disable system packages'
        if not ok and ("cannot disable" in out.lower() or "securityexception" in out.lower()):
            print(f"  ⚠️ OEM blocked disable for {pkg}. Attempting fallback ladder: 'uninstall --user {user_id}'...")
            ok_u, out_u = run_adb(prefix + ["shell", f"pm uninstall --user {user_id} {pkg}"])
            if ok_u and "success" in out_u.lower():
                return True, f"Disabled via uninstall ladder: {pkg}"

        # Parse potential new state line
        match = STATE_RE.search(out)
        if match:
            new_state = match.group(1).lower()
            if "disabled" in new_state:
                # Force-stop to kill any remaining background processes or wakelocks
                run_adb(prefix + ["shell", f"am force-stop {pkg}"])
                return True, f"Disabled: {pkg}"

        # Force-stop regardless and verify
        run_adb(prefix + ["shell", f"am force-stop {pkg}"])
        verified = get_package_state(pkg, user_id, serial)
        if verified == "disabled":
            return True, f"Disabled and verified: {pkg}"
        return False, f"Failed to disable {pkg}. Output: {out}"

    elif want == "uninstalled":
        ok, out = run_adb(prefix + ["shell", f"pm uninstall --user {user_id} {pkg}"])
        if not ok and ("only root can delete" in out.lower() or "delete_failed_user_restricted" in out.lower()):
            print(f"  ⚠️ Uninstall restricted by platform. Falling back to 'pm disable-user' ladder...")
            ok_d, out_d = run_adb(prefix + ["shell", f"pm disable-user --user {user_id} {pkg}"])
            run_adb(prefix + ["shell", f"am force-stop {pkg}"])
            verified = get_package_state(pkg, user_id, serial)
            if verified == "disabled":
                return True, f"Restricted uninstall resolved via disable: {pkg}"
            return False, f"Fallback disable failed: {out_d}"

        verified = get_package_state(pkg, user_id, serial)
        if verified == "uninstalled" or "success" in out.lower():
            return True, f"Uninstalled for user {user_id}: {pkg}"
        return False, f"Failed to uninstall {pkg}. Output: {out}"

    elif want == "enabled":
        # 1. If currently uninstalled, reinstall existing APK for user
        if current == "uninstalled":
            ok_re, out_re = run_adb(prefix + ["shell", f"cmd package install-existing --user {user_id} {pkg}"])
            if ok_re and "installed" in out_re.lower():
                return True, f"Reinstalled existing package: {pkg}"

        # 2. Try pm enable
        ok, out = run_adb(prefix + ["shell", f"pm enable --user {user_id} {pkg}"])
        match = STATE_RE.search(out)
        if match:
            new_state = match.group(1).lower()
            if "enabled" in new_state or "default" in new_state:
                return True, f"Enabled: {pkg}"
            if "disabled" in new_state:
                return False, f"Platform silently refused to enable {pkg} (remains disabled)"

        verified = get_package_state(pkg, user_id, serial)
        if verified == "enabled":
            return True, f"Enabled and verified: {pkg}"
        return False, f"Failed to enable {pkg}. Output: {out}"

    return False, f"Unknown target state: '{want}'"
