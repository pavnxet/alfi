#!/usr/bin/env python3
"""
tests/test_power_audit.py - Unit Tests for Empirical Battery Drain & Wakelock Proof Engine

Verifies:
- Duration string parsing (hours, minutes, seconds, milliseconds)
- dumpsys batterystats parsing (partial wakelocks, drain in mAh, screen off time)
- Reset batterystats command formulation
- Before-vs-after comparison calculations (percentage reductions)
"""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from power_audit import (
    parse_duration_to_ms,
    parse_batterystats,
    reset_batterystats,
    compare_power_metrics
)

SAMPLE_BATTERYSTATS_OUTPUT = """
Battery History:
  0 (10) 098 +screen +plugged
Statistics since last charge:
  System starts: 1, Currently running: 1
  Time on battery: 2h 30m 0s (100.0%)
  Screen on: 30m 0s (20.0%) 10x, Screen off: 2h 0m 0s (80.0%)
  Computed drain: 150.0, actual drain: 152.0-155.0

All partial wake locks:
  Wake lock 10045 com.facebook.katana: 15m 30s (45 times) realtime
  Wake lock 10080 com.google.android.gms: 8m 10s (80 times) realtime
  Wake lock 10112 com.aura.oobe.samsung: 4m 0s (12 times) realtime
"""

class TestPowerAudit(unittest.TestCase):

    def test_parse_duration_to_ms(self):
        """Test human duration parsing to milliseconds."""
        self.assertEqual(parse_duration_to_ms("30s"), 30000)
        self.assertEqual(parse_duration_to_ms("5m 10s"), 310000)
        self.assertEqual(parse_duration_to_ms("1h 0m 0s"), 3600000)
        self.assertEqual(parse_duration_to_ms("500ms"), 500)
        self.assertEqual(parse_duration_to_ms("1d 2h 3m 4s"), (86400 + 7200 + 180 + 4) * 1000)

    def test_parse_batterystats(self):
        """Test extraction of metrics from sample batterystats dump."""
        metrics = parse_batterystats(SAMPLE_BATTERYSTATS_OUTPUT)
        self.assertEqual(metrics["computed_drain_mah"], 150.0)
        self.assertEqual(metrics["screen_on_ms"], 30 * 60 * 1000)
        self.assertEqual(metrics["screen_off_ms"], 120 * 60 * 1000)
        self.assertEqual(metrics["total_wakelocks_count"], 45 + 80 + 12)

        culprits = metrics["top_wakelock_culprits"]
        self.assertTrue(len(culprits) >= 3)
        self.assertEqual(culprits[0]["package"], "com.facebook.katana")
        self.assertEqual(culprits[0]["count"], 45)
        self.assertEqual(culprits[0]["duration_ms"], (15 * 60 + 30) * 1000)

        # 150 mAh over 2.5 hours = 60.0 mAh/hr
        self.assertEqual(metrics["drain_rate_mah_per_hr"], 60.0)

    def test_reset_batterystats_dry_run(self):
        """Dry-run must simulate resetting batterystats."""
        ok, msg = reset_batterystats(dry_run=True)
        self.assertTrue(ok)
        self.assertIn("dumpsys batterystats --reset", msg)

    def test_compare_power_metrics(self):
        """Test calculation of percentage reductions between before and after."""
        before = {
            "total_wakelocks_count": 100,
            "total_wakelock_time_ms": 600000,
            "drain_rate_mah_per_hr": 40.0
        }
        after = {
            "total_wakelocks_count": 25,
            "total_wakelock_time_ms": 120000,
            "drain_rate_mah_per_hr": 10.0
        }

        diff = compare_power_metrics(before, after)

        self.assertEqual(diff["wakelock_count"]["before"], 100)
        self.assertEqual(diff["wakelock_count"]["after"], 25)
        self.assertEqual(diff["wakelock_count"]["percentage_change"], -75.0)

        self.assertEqual(diff["wakelock_time_ms"]["percentage_change"], -80.0)
        self.assertEqual(diff["drain_rate_mah_per_hr"]["percentage_change"], -75.0)

    def test_empty_batterystats_graceful(self):
        """Handle empty or malformed dumpsys gracefully."""
        metrics = parse_batterystats("")
        self.assertEqual(metrics["total_wakelocks_count"], 0)
        self.assertEqual(metrics["computed_drain_mah"], 0.0)
        self.assertEqual(metrics["drain_rate_mah_per_hr"], 0.0)

if __name__ == "__main__":
    unittest.main()
