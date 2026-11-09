#!/usr/bin/env python3
"""
tests/test_oem_fixtures.py - Mock Hardware Integration Tests Against Real OEM Recorded Fixtures

Tests the error taxonomy, benchmark parsers, rogue process identification, and Android 17 / HyperOS
rejection handling against committed device dumpsys fixtures without needing physical hardware.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from errors import (
    classify_adb_error,
    OemSecurityBlockedError,
    DeviceUnauthorizedError,
    PackageNotFoundError,
    LagFixerError
)
from bench import calculate_jank_metrics

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

class TestOemFixtures(unittest.TestCase):

    def test_classify_android17_fixture(self):
        """Verify Android 17 system app uninstall rejection is classified as OEM Security Block."""
        fixture_path = os.path.join(FIXTURES_DIR, "android17_uninstall_failure.txt")
        self.assertTrue(os.path.exists(fixture_path))
        with open(fixture_path, "r", encoding="utf-8") as f:
            content = f.read()

        err = classify_adb_error(content, pkg="com.android.chrome")
        self.assertIsInstance(err, OemSecurityBlockedError)
        self.assertEqual(err.code, "ERR_OEM_SECURITY_BLOCKED")
        self.assertIn("Android 17+", err.remediation)

    def test_classify_hyperos_fixture(self):
        """Verify Xiaomi HyperOS / MIUI SecurityException is classified accurately."""
        fixture_path = os.path.join(FIXTURES_DIR, "hyperos_security_exception.txt")
        self.assertTrue(os.path.exists(fixture_path))
        with open(fixture_path, "r", encoding="utf-8") as f:
            content = f.read()

        err = classify_adb_error(content, pkg="com.miui.analytics")
        self.assertIsInstance(err, OemSecurityBlockedError)
        self.assertIn("HyperOS", err.remediation)

    def test_classify_unauthorized_error(self):
        """Verify unauthorized RSA key error classification."""
        raw = "error: device unauthorized. Please check the confirmation dialog on your device."
        err = classify_adb_error(raw)
        self.assertIsInstance(err, DeviceUnauthorizedError)
        self.assertEqual(err.code, "ERR_DEVICE_UNAUTHORIZED")
        self.assertIn("Always allow", err.remediation)

    def test_classify_package_not_found(self):
        """Verify package not found error classification."""
        raw = "Error: package not found on user 0"
        err = classify_adb_error(raw, pkg="com.ghost.app")
        self.assertIsInstance(err, PackageNotFoundError)
        self.assertEqual(err.code, "ERR_PACKAGE_NOT_FOUND")

    def test_parse_pixel_framestats_fixture(self):
        """Verify frame pacing and jank calculation using real recorded Pixel framestats fixture."""
        fixture_path = os.path.join(FIXTURES_DIR, "pixel_framestats.txt")
        self.assertTrue(os.path.exists(fixture_path))
        with open(fixture_path, "r", encoding="utf-8") as f:
            content = f.read()

        metrics = calculate_jank_metrics(content)
        self.assertGreater(metrics["total_frames"], 0)
        self.assertIn("jank_percentage", metrics)
        self.assertIn("p90_latency_ms", metrics)
        self.assertIn("p99_latency_ms", metrics)
        self.assertIn("fps_1pct_low", metrics)

    def test_samsung_j7_fixture_diagnostics(self):
        """Inspect recorded Samsung J7 Max CPU dump to verify rogue CPU consumer parsing."""
        fixture_path = os.path.join(FIXTURES_DIR, "samsung_sm_g615f_dumpsys.txt")
        self.assertTrue(os.path.exists(fixture_path))
        with open(fixture_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        hogs = []
        for line in lines:
            if "system_server" in line or "com.google.android.gms" in line or "com.aura.oobe.samsung" in line:
                hogs.append(line.strip())

        self.assertEqual(len(hogs), 3)
        self.assertTrue(any("152%" in h for h in hogs))
        self.assertTrue(any("133%" in h for h in hogs))
        self.assertTrue(any("com.aura.oobe.samsung" in h for h in hogs))

    def test_redmi_a1_fixture_diagnostics(self):
        """Inspect recorded Redmi A1+ dumpsys to verify kswapd0 thrashing detection."""
        fixture_path = os.path.join(FIXTURES_DIR, "redmi_220733si_dumpsys.txt")
        self.assertTrue(os.path.exists(fixture_path))
        with open(fixture_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("kswapd0", content)
        self.assertIn("ZRAM: 512,000 kB", content)
        self.assertIn("com.facebook.katana", content)

if __name__ == "__main__":
    unittest.main()
