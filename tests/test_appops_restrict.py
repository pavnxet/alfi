#!/usr/bin/env python3
"""
tests/test_appops_restrict.py - Comprehensive Unit Tests for Phase 2 AppOps & Standby Bucket Engine

Verifies background restriction logic, standby bucket assignments, pre-flight snapshot
manifests, rollback mechanisms, input validation, and injection defenses using standard
library unittest and unittest.mock without requiring a physical device or pip dependencies.
"""

import sys
import os
import unittest
import json
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from appops_restrict import (
    get_appops_state,
    get_standby_bucket,
    set_appops_restriction,
    set_standby_bucket,
    create_appops_manifest,
    VALID_BUCKETS
)
from connect import validate_package_name

class TestAppOpsRestrict(unittest.TestCase):

    def test_validate_package_names(self):
        """Ensure package name validator permits legitimate packages and thwarts injection attempts."""
        valid_pkgs = [
            "com.instagram.android",
            "com.facebook.katana",
            "com.twitter.android",
            "com.snapchat.android",
            "com.truecaller",
            "org.telegram.messenger"
        ]
        for p in valid_pkgs:
            self.assertTrue(validate_package_name(p), f"Legitimate package rejected: {p}")

        invalid_pkgs = [
            "com.app; reboot",
            "com.app$(rm -rf /)",
            "com.app`whoami`",
            "com.app && ls",
            "singleword",
            "",
            "   "
        ]
        for p in invalid_pkgs:
            self.assertFalse(validate_package_name(p), f"Malicious/malformed package allowed: {p}")

    def test_dry_run_appops_restriction(self):
        """Dry-run must formulate and display the AppOps commands without executing."""
        ok, msg = set_appops_restriction("com.instagram.android", mode="ignore", dry_run=True)
        self.assertTrue(ok)
        self.assertIn("[DRY-RUN]", msg)
        self.assertIn("cmd appops set com.instagram.android RUN_IN_BACKGROUND ignore", msg)
        self.assertIn("cmd appops set com.instagram.android RUN_ANY_IN_BACKGROUND ignore", msg)

    def test_dry_run_standby_bucket(self):
        """Dry-run must preview the standby bucket command."""
        ok, msg = set_standby_bucket("com.instagram.android", bucket="restricted", dry_run=True)
        self.assertTrue(ok)
        self.assertIn("[DRY-RUN]", msg)
        self.assertIn("am set-standby-bucket com.instagram.android restricted", msg)

    def test_invalid_standby_bucket_rejected(self):
        """Reject invalid standby buckets outside official Android specifications."""
        ok, msg = set_standby_bucket("com.instagram.android", bucket="dormant_sleep")
        self.assertFalse(ok)
        self.assertIn("Invalid standby bucket", msg)

    @patch("appops_restrict.run_adb")
    def test_successful_appops_restriction(self, mock_run_adb):
        """Simulate successful ADB execution for RUN_IN_BACKGROUND and RUN_ANY_IN_BACKGROUND."""
        mock_run_adb.return_value = (True, "")
        ok, msg = set_appops_restriction("com.facebook.katana", mode="ignore", serial="MOCK_DEVICE_1")
        self.assertTrue(ok)
        self.assertIn("restricted (blocked from background execution)", msg)
        self.assertEqual(mock_run_adb.call_count, 2)
        mock_run_adb.assert_any_call(["-s", "MOCK_DEVICE_1", "shell", "cmd appops set com.facebook.katana RUN_IN_BACKGROUND ignore"])
        mock_run_adb.assert_any_call(["-s", "MOCK_DEVICE_1", "shell", "cmd appops set com.facebook.katana RUN_ANY_IN_BACKGROUND ignore"])

    @patch("appops_restrict.run_adb")
    def test_failed_appops_restriction(self, mock_run_adb):
        """Simulate ADB failure during AppOps configuration."""
        mock_run_adb.return_value = (False, "Error: package not found")
        ok, msg = set_appops_restriction("com.nonexistent.app", mode="ignore", serial="MOCK_DEVICE_1")
        self.assertFalse(ok)
        self.assertIn("Failed to set AppOps for com.nonexistent.app", msg)

    @patch("appops_restrict.run_adb")
    def test_successful_standby_bucket_assignment(self, mock_run_adb):
        """Simulate setting standby bucket to restricted."""
        mock_run_adb.return_value = (True, "")
        ok, msg = set_standby_bucket("com.facebook.katana", bucket="restricted", serial="MOCK_DEVICE_1")
        self.assertTrue(ok)
        self.assertIn("Standby bucket for com.facebook.katana -> 'restricted'", msg)
        mock_run_adb.assert_called_once_with(["-s", "MOCK_DEVICE_1", "shell", "am set-standby-bucket com.facebook.katana restricted"])

    @patch("appops_restrict.run_adb")
    def test_get_appops_state_parsing(self, mock_run_adb):
        """Test parsing of different AppOps query outputs."""
        # 1. Ignore
        mock_run_adb.return_value = (True, "Uid mode: RUN_IN_BACKGROUND: ignore\n")
        self.assertEqual(get_appops_state("com.instagram.android"), "ignore")

        # 2. Allow
        mock_run_adb.return_value = (True, "Uid mode: RUN_IN_BACKGROUND: allow\n")
        self.assertEqual(get_appops_state("com.instagram.android"), "allow")

        # 3. Default / unknown
        mock_run_adb.return_value = (True, "No operations found\n")
        self.assertEqual(get_appops_state("com.instagram.android"), "default")

    @patch("appops_restrict.run_adb")
    def test_get_standby_bucket_parsing(self, mock_run_adb):
        """Test numeric and string standby bucket code translation."""
        # 45 -> restricted
        mock_run_adb.return_value = (True, "45\n")
        self.assertEqual(get_standby_bucket("com.instagram.android"), "restricted")

        # 10 -> active
        mock_run_adb.return_value = (True, "10\n")
        self.assertEqual(get_standby_bucket("com.instagram.android"), "active")

        # String representation -> rare
        mock_run_adb.return_value = (True, "rare\n")
        self.assertEqual(get_standby_bucket("com.instagram.android"), "rare")

    def test_create_appops_manifest_and_rollback_structure(self):
        """Ensure snapshot manifest is created with package states and valid rollback instructions."""
        device_info = {
            "model": "SM-G615F",
            "manufacturer": "samsung",
            "android_version": "8.1.0",
            "build_id": "M1AJQ"
        }
        packages_state = [
            {"package": "com.facebook.katana", "orig_appops": "allow", "orig_bucket": "active"},
            {"package": "com.instagram.android", "orig_appops": "default", "orig_bucket": "working_set"}
        ]
        manifest_path = create_appops_manifest("MOCK_SERIAL_ABC", device_info, packages_state)

        self.assertTrue(os.path.exists(manifest_path))
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["type"], "appops_standby_reset_point")
        self.assertEqual(data["device"]["serial"], "MOCK_SERIAL_ABC")
        self.assertEqual(len(data["packages"]), 2)
        self.assertEqual(data["packages"][0]["package"], "com.facebook.katana")
        self.assertIn("--reset-manifest", data["reset_command"])

        # Clean up temporary test manifest
        if os.path.exists(manifest_path):
            os.remove(manifest_path)

if __name__ == "__main__":
    unittest.main()
