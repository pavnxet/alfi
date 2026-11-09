#!/usr/bin/env python3
"""
tests/test_doze_boost.py - Unit Tests for Deep Doze Enforcement & Allowlist Auditor

Verifies:
- dumpsys deviceidle whitelist parsing (system vs user exemptions)
- Safe candidate detection (finding rogue battery hogs in whitelist)
- Hard protection for phone telephony and System UI
- Pre-flight snapshot creation and manifest restoration
- Force-idle state execution
"""

import sys
import os
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from doze_boost import (
    parse_deviceidle_whitelist,
    remove_from_whitelist,
    add_to_whitelist,
    force_idle_state,
    audit_and_clean_whitelist,
    restore_doze_manifest,
    DOZE_SYSTEM_ALLOWLIST
)

SAMPLE_DEVICEIDLE_OUTPUT = """
System whitelist:
  system,com.android.phone,1001
  system,com.android.systemui,1002
  system,com.google.android.gms,10023
  system,com.aura.oobe.samsung,10150
User whitelist:
  user,com.facebook.katana,10234
  user,com.instagram.android,10245
  user,com.whatsapp,10280
"""

class TestDozeBoost(unittest.TestCase):

    def test_parse_deviceidle_whitelist(self):
        """Ensure parser cleanly categorizes system vs user whitelisted packages."""
        data = parse_deviceidle_whitelist(SAMPLE_DEVICEIDLE_OUTPUT)
        self.assertIn("com.android.phone", data["system"])
        self.assertIn("com.android.systemui", data["system"])
        self.assertIn("com.google.android.gms", data["system"])
        self.assertIn("com.aura.oobe.samsung", data["system"])

        self.assertIn("com.facebook.katana", data["user"])
        self.assertIn("com.instagram.android", data["user"])
        self.assertIn("com.whatsapp", data["user"])

        self.assertEqual(len(data["all"]), 7)

    def test_protection_for_system_allowlist(self):
        """Refuse to remove essential phone subsystems from the Doze whitelist."""
        for pkg in DOZE_SYSTEM_ALLOWLIST:
            ok, msg = remove_from_whitelist(pkg, dry_run=True)
            self.assertFalse(ok)
            self.assertIn("critical phone subsystem", msg)

    def test_remove_from_whitelist_dry_run(self):
        """Dry-run must return planned adb command without executing ADB."""
        pkg = "com.facebook.katana"
        ok, msg = remove_from_whitelist(pkg, dry_run=True)
        self.assertTrue(ok)
        self.assertIn(f"cmd deviceidle whitelist -{pkg}", msg)

    def test_add_to_whitelist_dry_run(self):
        """Dry-run restoration must return planned adb command."""
        pkg = "com.facebook.katana"
        ok, msg = add_to_whitelist(pkg, dry_run=True)
        self.assertTrue(ok)
        self.assertIn(f"cmd deviceidle whitelist +{pkg}", msg)

    def test_invalid_package_name_rejected(self):
        """Reject command injection attempts."""
        ok, msg = remove_from_whitelist("com.bad; rm -rf /", dry_run=True)
        self.assertFalse(ok)
        self.assertIn("Invalid package name", msg)

    def test_force_idle_state_dry_run(self):
        """Dry-run must simulate force-idle state trigger."""
        ok, msg = force_idle_state(dry_run=True)
        self.assertTrue(ok)
        self.assertIn("cmd deviceidle force-idle", msg)

    def test_audit_and_clean_whitelist_simulation(self):
        """Detect known tracking and bloat culprits in allowlist."""
        with patch("doze_boost.get_current_whitelist", return_value=parse_deviceidle_whitelist(SAMPLE_DEVICEIDLE_OUTPUT)):
            res = audit_and_clean_whitelist(clean=True, dry_run=True)
            self.assertIn("com.aura.oobe.samsung", res["culprits_found"])
            self.assertIn("com.facebook.katana", res["culprits_found"])
            self.assertIn("com.instagram.android", res["culprits_found"])
            self.assertNotIn("com.whatsapp", res["culprits_found"])  # WhatsApp is not considered generic bloat
            self.assertEqual(len(res["removed"]), 3)

    def test_restore_doze_manifest(self):
        """Test reading a manifest JSON and generating restoration calls."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            json.dump({
                "whitelist": {
                    "user": ["com.facebook.katana", "com.instagram.android"]
                }
            }, tf)
            manifest_file = tf.name

        try:
            res = restore_doze_manifest(manifest_file, dry_run=True)
            self.assertTrue(res["success"])
            self.assertIn("com.facebook.katana", res["restored"])
            self.assertIn("com.instagram.android", res["restored"])
        finally:
            if os.path.exists(manifest_file):
                os.remove(manifest_file)

if __name__ == "__main__":
    unittest.main()
