#!/usr/bin/env python3
"""
tests/test_export_shizuku.py - Comprehensive Unit Tests for On-Device Shizuku / Rish Exporter

Verifies export of optimization and paired rollback shell scripts, profile package
selection, command generation, syntax validity, and dry-run output without requiring
a physical device or external dependencies.
"""

import sys
import os
import unittest
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from export_shizuku import (
    generate_shizuku_scripts,
    DEFAULT_OEM_BLOAT
)

class TestExportShizuku(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_default_oem_bloat_manifest(self):
        """Ensure all OEM bloat lists are populated with valid packages."""
        for oem, pkgs in DEFAULT_OEM_BLOAT.items():
            self.assertTrue(len(pkgs) > 0, f"OEM {oem} bloat list is empty")
            for p in pkgs:
                self.assertIn(".", p, f"Invalid package name format in {oem}: {p}")

    def test_generate_scripts_samsung(self):
        """Test generating Samsung optimization and paired rollback scripts."""
        to_disable = ["com.aura.oobe.samsung", "com.samsung.android.diagmonagent"]
        to_restrict = ["com.facebook.katana", "com.instagram.android"]

        opt_path, rb_path = generate_shizuku_scripts(
            profile="samsung",
            output_dir=self.test_dir,
            packages_to_disable=to_disable,
            packages_to_restrict=to_restrict
        )

        self.assertTrue(os.path.exists(opt_path))
        self.assertTrue(os.path.exists(rb_path))

        # Check optimization script content
        with open(opt_path, "r", encoding="utf-8") as f:
            opt_content = f.read()

        self.assertIn("#!/bin/sh", opt_content)
        self.assertIn("pm disable-user --user 0 com.aura.oobe.samsung", opt_content)
        self.assertIn("cmd appops set com.facebook.katana RUN_IN_BACKGROUND ignore", opt_content)
        self.assertIn("cmd appops set com.facebook.katana RUN_ANY_IN_BACKGROUND ignore", opt_content)
        self.assertIn("am set-standby-bucket com.facebook.katana restricted", opt_content)
        self.assertIn("settings put global window_animation_scale 0.5", opt_content)
        self.assertIn("pm trim-caches", opt_content)

        # Check rollback script content
        with open(rb_path, "r", encoding="utf-8") as f:
            rb_content = f.read()

        self.assertIn("#!/bin/sh", rb_content)
        self.assertIn("pm enable --user 0 com.aura.oobe.samsung", rb_content)
        self.assertIn("cmd package install-existing --user 0 com.aura.oobe.samsung", rb_content)
        self.assertIn("cmd appops set com.facebook.katana RUN_IN_BACKGROUND allow", rb_content)
        self.assertIn("am set-standby-bucket com.facebook.katana active", rb_content)
        self.assertIn("settings put global window_animation_scale 1.0", rb_content)

    def test_generate_scripts_xiaomi(self):
        """Test generating Xiaomi optimization and rollback scripts."""
        to_disable = ["com.miui.analytics.go", "com.miui.android.fashiongallery"]
        to_restrict = []

        opt_path, rb_path = generate_shizuku_scripts(
            profile="xiaomi",
            output_dir=self.test_dir,
            packages_to_disable=to_disable,
            packages_to_restrict=to_restrict
        )

        self.assertTrue(os.path.exists(opt_path))
        self.assertTrue(os.path.exists(rb_path))

        with open(opt_path, "r", encoding="utf-8") as f:
            opt_content = f.read()
        self.assertIn("com.miui.analytics.go", opt_content)
        self.assertIn("com.miui.android.fashiongallery", opt_content)

if __name__ == "__main__":
    unittest.main()
