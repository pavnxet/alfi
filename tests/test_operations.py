#!/usr/bin/env python3
"""
tests/test_operations.py - Unit tests for package state validation & Android 17 resolution
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from operations import validate_package_name, apply_package_state

class TestOperations(unittest.TestCase):

    def test_validate_package_name_valid(self):
        self.assertTrue(validate_package_name("com.android.chrome"))
        self.assertTrue(validate_package_name("com.facebook.katana"))
        self.assertTrue(validate_package_name("org.videolan.vlc"))
        self.assertTrue(validate_package_name("com.example.app_one"))

    def test_validate_package_name_invalid_injection(self):
        self.assertFalse(validate_package_name("com.example; rm -rf /"))
        self.assertFalse(validate_package_name("com.app$(whoami)"))
        self.assertFalse(validate_package_name("com.app | cat /etc/passwd"))
        self.assertFalse(validate_package_name(""))
        self.assertFalse(validate_package_name("invalid_single_word"))

    def test_dry_run_state_application(self):
        ok, msg = apply_package_state("com.android.chrome", want="disabled", dry_run=True)
        self.assertTrue(ok)
        self.assertIn("[DRY-RUN]", msg)
        self.assertIn("pm disable-user --user 0 com.android.chrome", msg)

    def test_android_17_uninstall_fallback(self):
        # SDK 37 (Android 17) must fall back from uninstalled to disabled
        ok, msg = apply_package_state("com.android.chrome", want="uninstalled", sdk_level=37, dry_run=True)
        self.assertTrue(ok)
        self.assertIn("pm disable-user", msg)

if __name__ == "__main__":
    unittest.main()
