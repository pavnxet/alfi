#!/usr/bin/env python3
"""
scripts/errors.py - Standardized Error Taxonomy & Actionable Recovery Engine

Translates low-level ADB failures, permission refusals, and OEM security blocks into
human-readable diagnoses paired with specific next-step remediation commands.
"""

import sys
from typing import Dict, Any

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

class LagFixerError(Exception):
    """Base exception for all lag-fixer errors."""
    def __init__(self, message: str, remediation: str = "", code: str = "ERR_GENERAL"):
        super().__init__(message)
        self.message = message
        self.remediation = remediation
        self.code = code

    def format_human(self) -> str:
        res = f"❌ {self.message}"
        if self.remediation:
            res += f"\n💡 Remediation: {self.remediation}"
        return res

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.code,
            "message": self.message,
            "remediation": self.remediation
        }

class AdbNotFoundError(LagFixerError):
    """Raised when adb binary is not in PATH or platform-tools."""
    def __init__(self):
        super().__init__(
            message="Android Debug Bridge (adb) was not found on your system.",
            remediation="Install Android SDK Platform-Tools or run 'python scripts/connect.py' to guide setup.",
            code="ERR_ADB_NOT_FOUND"
        )

class NoDeviceConnectedError(LagFixerError):
    """Raised when no Android device is attached."""
    def __init__(self):
        super().__init__(
            message="No Android phone is connected to your computer.",
            remediation="Plug in your phone via USB data cable or pair wirelessly using 'python scripts/connect.py --pair IP:PORT CODE'.",
            code="ERR_NO_DEVICE"
        )

class DeviceUnauthorizedError(LagFixerError):
    """Raised when device is connected but RSA key is not authorized."""
    def __init__(self, serial: str = ""):
        target = f" ({serial})" if serial else ""
        super().__init__(
            message=f"Connected device{target} is unauthorized.",
            remediation="Unlock your phone screen and tap 'Always allow from this computer' on the USB Debugging prompt.",
            code="ERR_DEVICE_UNAUTHORIZED"
        )

class PackageNotFoundError(LagFixerError):
    """Raised when the specified package does not exist on the device."""
    def __init__(self, package_name: str):
        super().__init__(
            message=f"Package '{package_name}' was not found on this device.",
            remediation=f"Verify package name via 'adb shell pm list packages | grep {package_name}'.",
            code="ERR_PACKAGE_NOT_FOUND"
        )

class OemSecurityBlockedError(LagFixerError):
    """Raised when an OEM system protection refuses package mutation."""
    def __init__(self, package_name: str, oem_reason: str = ""):
        reason_str = f" ({oem_reason})" if oem_reason else ""
        super().__init__(
            message=f"OEM system protection blocked modifying '{package_name}'{reason_str}.",
            remediation="HyperOS / MIUI requires toggling 'MIUI Optimization' or 'USB debugging (Security settings)'. On Android 17+, system uninstall is blocked; use 'scripts/operations.py' to disable instead.",
            code="ERR_OEM_SECURITY_BLOCKED"
        )

class VerificationFailedError(LagFixerError):
    """Raised when adb exited with code 0 but dumpsys confirmed the state was not applied."""
    def __init__(self, package_name: str, expected_state: str, actual_state: str):
        super().__init__(
            message=f"State verification failed for '{package_name}': wanted '{expected_state}', but device reported '{actual_state}'.",
            remediation=f"The OEM platform silently ignored the command. Try fallback ladder or check 'scripts/rescue.py'.",
            code="ERR_VERIFICATION_FAILED"
        )

def classify_adb_error(stderr_text: str, pkg: str = "") -> LagFixerError:
    """Analyze ADB error output and return the corresponding specialized error."""
    text = (stderr_text or "").lower()
    if "only root can delete" in text or "delete_failed_user_restricted" in text:
        return OemSecurityBlockedError(pkg, "Android 17+ blocks user-space system uninstall")
    if "cannot disable system packages" in text:
        return OemSecurityBlockedError(pkg, "HyperOS / MIUI blocked disabling system package")
    if "device unauthorized" in text or "unauthorized" in text:
        return DeviceUnauthorizedError()
    if "no devices" in text or "device not found" in text:
        return NoDeviceConnectedError()
    if "not found" in text and pkg:
        return PackageNotFoundError(pkg)
    return LagFixerError(f"ADB execution failed: {stderr_text}", "Check USB connection and device screen.")
