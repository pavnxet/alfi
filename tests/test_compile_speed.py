#!/usr/bin/env python3
"""
tests/test_compile_speed.py - Comprehensive Unit Tests for Phase 1 ART Pre-Compilation & Reset Engine

Tests package validation, dry-run simulations, compilation status parsing,
mocked ADB execution, manifest reset points, and failure handling without
requiring a physical Android device or external pip dependencies.
"""

import sys
import os
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from compile_speed import (
    compile_package,
    reset_package_compilation,
    create_compile_manifest,
    get_package_compile_status,
    VALID_FILTERS
)
from connect import validate_package_name

class TestCompileSpeed(unittest.TestCase):

    def test_validate_package_names(self):
        """Ensure package name validator accepts valid packages and catches injection attacks."""
        valid = ["com.android.settings", "com.sec.android.launcher", "org.mozilla.firefox", "app_one.test.pkg"]
        for p in valid:
            self.assertTrue(validate_package_name(p), f"Failed for valid package: {p}")

        invalid = [
            "com.app; rm -rf /",
            "com.app$(whoami)",
            "com.app && reboot",
            "com.app | cat /etc/hosts",
            "",
            "singleword",
            "   "
        ]
        for p in invalid:
            self.assertFalse(validate_package_name(p), f"Did not catch invalid package: {p}")

    def test_dry_run_compilation(self):
        """Dry-run must return the planned command without executing ADB."""
        ok, msg = compile_package("com.android.settings", compile_filter="speed-profile", dry_run=True)
        self.assertTrue(ok)
        self.assertIn("[DRY-RUN]", msg)
        self.assertIn("cmd package compile -m speed-profile -f com.android.settings", msg)

    def test_dry_run_reset(self):
        """Dry-run reset must preview the reset command."""
        ok, msg = reset_package_compilation("com.android.settings", dry_run=True)
        self.assertTrue(ok)
        self.assertIn("[DRY-RUN]", msg)
        self.assertIn("cmd package compile --reset com.android.settings", msg)

    def test_invalid_filter_rejection(self):
        """Invalid compilation filters must be rejected cleanly."""
        ok, msg = compile_package("com.android.settings", compile_filter="ultra-turbo", dry_run=False)
        self.assertFalse(ok)
        self.assertIn("Invalid compilation filter", msg)

    @patch("compile_speed.run_adb")
    def test_successful_compilation(self, mock_run_adb):
        """Simulate successful ADB package compilation."""
        mock_run_adb.return_value = (True, "Success\n")
        ok, msg = compile_package("com.android.settings", compile_filter="speed", serial="mock_device")
        self.assertTrue(ok)
        self.assertIn("Compiled com.android.settings with filter 'speed'", msg)
        mock_run_adb.assert_called_once_with(
            ["-s", "mock_device", "shell", "cmd package compile -m speed -f com.android.settings"],
            timeout=90
        )

    @patch("compile_speed.run_adb")
    def test_filter_type_keyword_alias(self, mock_run_adb):
        """Passing filter_type as kwarg must map transparently to compile_filter."""
        mock_run_adb.return_value = (True, "Success\n")
        ok, msg = compile_package("com.instagram.android", filter_type="speed-profile", serial="mock_device")
        self.assertTrue(ok)
        mock_run_adb.assert_called_once_with(
            ["-s", "mock_device", "shell", "cmd package compile -m speed-profile -f com.instagram.android"],
            timeout=90
        )

    @patch("compile_speed.run_adb")
    def test_compilation_failure(self, mock_run_adb):
        """Simulate ADB compilation failure."""
        mock_run_adb.return_value = (False, "Failure [INSTALL_FAILED_INVALID_APK]")
        ok, msg = compile_package("com.android.settings", compile_filter="speed-profile", serial="mock_device")
        self.assertFalse(ok)
        self.assertIn("Compilation failed for com.android.settings", msg)

    @patch("compile_speed.run_adb")
    def test_successful_reset(self, mock_run_adb):
        """Simulate successful compilation reset."""
        mock_run_adb.return_value = (True, "Success\n")
        ok, msg = reset_package_compilation("com.android.settings", serial="mock_device")
        self.assertTrue(ok)
        self.assertIn("reverted to default JIT state", msg)
        mock_run_adb.assert_called_once_with(
            ["-s", "mock_device", "shell", "cmd package compile --reset com.android.settings"],
            timeout=30
        )

    @patch("compile_speed.run_adb")
    def test_get_compile_status(self, mock_run_adb):
        """Simulate dumpsys package status extraction."""
        mock_output = """
        Package [com.android.settings] (32a8ff9):
          compileReason=speed-profile
          status=3
        """
        mock_run_adb.return_value = (True, mock_output)
        status = get_package_compile_status("com.android.settings")
        self.assertIn("compileReason=speed-profile", status)

    def test_create_compile_manifest(self):
        """Ensure reset manifest is properly created with rollback command."""
        device_info = {
            "model": "SM-G615F",
            "manufacturer": "samsung",
            "android_version": "8.1.0",
            "build_id": "M1AJQ"
        }
        packages = ["com.android.settings", "com.sec.android.launcher"]
        manifest_path = create_compile_manifest("mock_serial_123", device_info, packages, "speed-profile")
        
        self.assertTrue(os.path.exists(manifest_path))
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        self.assertEqual(data["type"], "art_compilation_reset_point")
        self.assertEqual(data["compile_filter"], "speed-profile")
        self.assertEqual(data["packages"], packages)
        self.assertIn("--reset-manifest", data["reset_command"])
        
        # Cleanup
        if os.path.exists(manifest_path):
            os.remove(manifest_path)

if __name__ == "__main__":
    unittest.main()
