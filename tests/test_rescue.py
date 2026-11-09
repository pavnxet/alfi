#!/usr/bin/env python3
"""
tests/test_rescue.py - Comprehensive Unit Tests for Phase 3 Emergency Feature Rescue Engine

Verifies critical system component repair, deep package rescue (enable, reinstall,
AppOps reset, Standby reset, ART reset), pre-rescue snapshots, and hardware Safe Mode
recovery guides without requiring a physical device or external pip packages.
"""

import sys
import os
import unittest
import json
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from rescue import (
    get_disabled_packages,
    create_rescue_snapshot,
    rescue_single_package,
    CRITICAL_SYSTEM_COMPONENTS,
    SAFE_MODE_GUIDES,
    find_all_manifests
)
from connect import validate_package_name

class TestRescue(unittest.TestCase):

    def test_critical_components_manifest(self):
        """Ensure all critical components are registered and contain legitimate package names."""
        for cat, pkgs in CRITICAL_SYSTEM_COMPONENTS.items():
            self.assertTrue(len(pkgs) > 0, f"Category '{cat}' is empty")
            for p in pkgs:
                self.assertTrue(validate_package_name(p), f"Invalid package name in critical category: {p}")

    def test_safe_mode_guides(self):
        """Ensure all supported OEMs have hardware button safe mode recovery instructions."""
        expected_oems = ["samsung", "xiaomi", "google", "realme_oneplus", "general"]
        for oem in expected_oems:
            self.assertIn(oem, SAFE_MODE_GUIDES)
            self.assertTrue(len(SAFE_MODE_GUIDES[oem]) > 20)

    @patch("rescue.run_adb")
    def test_get_disabled_packages_parsing(self, mock_run_adb):
        """Simulate pm list packages -d parsing."""
        mock_output = (
            "package:com.aura.oobe.samsung\n"
            "package:com.samsung.android.diagmonagent\n"
            "package:com.sec.android.app.billing\n"
        )
        mock_run_adb.return_value = (True, mock_output)
        pkgs = get_disabled_packages(serial="MOCK_DEV", user_id=0)
        self.assertEqual(len(pkgs), 3)
        self.assertIn("com.aura.oobe.samsung", pkgs)
        self.assertIn("com.samsung.android.diagmonagent", pkgs)
        self.assertIn("com.sec.android.app.billing", pkgs)

    @patch("rescue.run_adb")
    def test_get_disabled_packages_empty(self, mock_run_adb):
        """Handle scenario with zero disabled packages."""
        mock_run_adb.return_value = (True, "")
        pkgs = get_disabled_packages(serial="MOCK_DEV")
        self.assertEqual(pkgs, [])

    def test_create_rescue_snapshot(self):
        """Ensure pre-rescue snapshot creates structured JSON with disabled package state."""
        device_info = {
            "model": "SM-G615F",
            "manufacturer": "samsung",
            "android_version": "8.1.0",
            "sdk_level": 27
        }
        disabled = ["com.aura.oobe.samsung", "com.sec.android.app.billing"]
        snapshot_path = create_rescue_snapshot("MOCK_SERIAL", device_info, disabled, "test_rescue")

        self.assertTrue(os.path.exists(snapshot_path))
        with open(snapshot_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["type"], "rescue_pre_flight_snapshot")
        self.assertEqual(data["action"], "test_rescue")
        self.assertEqual(data["disabled_packages_count"], 2)
        self.assertEqual(data["disabled_packages"], disabled)

        # Cleanup
        if os.path.exists(snapshot_path):
            os.remove(snapshot_path)

    @patch("rescue.apply_package_state")
    @patch("rescue.run_adb")
    def test_rescue_single_package_success(self, mock_run_adb, mock_apply_state):
        """Simulate deep package rescue verifying enable, install-existing, appops, bucket and compile resets."""
        mock_apply_state.return_value = (True, "Enabled com.android.settings")
        mock_run_adb.return_value = (True, "Package com.android.settings installed for user: 0")

        res = rescue_single_package("com.android.settings", serial="MOCK_DEV", user_id=0, sdk_level=31)
        self.assertTrue(res["success"])
        self.assertEqual(res["package"], "com.android.settings")
        self.assertTrue(any("Enabled com.android.settings" in a for a in res["actions"]))
        self.assertTrue(any("AppOps reset -> allow" in a for a in res["actions"]))
        self.assertTrue(any("Standby bucket reset -> active" in a for a in res["actions"]))
        self.assertTrue(any("ART JIT compilation reset" in a for a in res["actions"]))

    def test_rescue_invalid_package_rejected(self):
        """Injection attacks must be caught and rejected cleanly."""
        res = rescue_single_package("com.app; reboot")
        self.assertFalse(res["success"])
        self.assertIn("Invalid package name", res["error"])

    def test_dry_run_rescue(self):
        """Dry-run must formulate and display planned actions without calling mutating commands."""
        res = rescue_single_package("com.google.android.gms", dry_run=True)
        self.assertTrue(res["success"])
        self.assertTrue(any("[DRY-RUN]" in a for a in res["actions"]))

    def test_find_all_manifests(self):
        """Ensure manifest locator scans backups/ directory properly."""
        manifests = find_all_manifests()
        self.assertIsInstance(manifests, list)

if __name__ == "__main__":
    unittest.main()
