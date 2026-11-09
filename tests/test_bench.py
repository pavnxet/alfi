import unittest
from unittest.mock import patch
import sys
import os

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from bench import (
    get_screen_dimensions,
    get_display_refresh_rate,
    calculate_jank_metrics,
    compare_benchmarks
)

class TestBench(unittest.TestCase):

    @patch("bench.run_adb")
    def test_get_screen_dimensions_physical(self, mock_run):
        mock_run.return_value = (True, "Physical size: 1080x2400\n")
        w, h = get_screen_dimensions("test_serial")
        self.assertEqual(w, 1080)
        self.assertEqual(h, 2400)

    @patch("bench.run_adb")
    def test_get_screen_dimensions_override(self, mock_run):
        mock_run.return_value = (True, "Physical size: 1440x3120\nOverride size: 1080x2340\n")
        w, h = get_screen_dimensions("test_serial")
        self.assertEqual(w, 1080)
        self.assertEqual(h, 2340)

    @patch("bench.run_adb")
    def test_get_screen_dimensions_fallback(self, mock_run):
        mock_run.return_value = (False, "")
        w, h = get_screen_dimensions("test_serial")
        self.assertEqual(w, 1080)
        self.assertEqual(h, 2400)

    @patch("bench.run_adb")
    def test_get_display_refresh_rate_setting(self, mock_run):
        mock_run.side_effect = [(True, "120.0\n")]
        hz = get_display_refresh_rate("test_serial")
        self.assertEqual(hz, 120.0)

    @patch("bench.run_adb")
    def test_get_display_refresh_rate_dumpsys(self, mock_run):
        mock_run.side_effect = [
            (False, ""),
            (True, "DisplayDeviceInfo{... fps: 90.0 ...}")
        ]
        hz = get_display_refresh_rate("test_serial")
        self.assertEqual(hz, 90.0)

    def test_calculate_jank_metrics_insufficient(self):
        res = calculate_jank_metrics("", min_frames=10)
        self.assertIn("error", res)
        self.assertEqual(res["total_frames"], 0)

    def test_calculate_jank_metrics_valid(self):
        sample_framestats = """
---PROFILEDATA---
Flags,IntendedVsync,Vsync,OldestInput,NewestInput,HandleInput,Anim,Perform,Draw,SyncQ,SyncStart,IssueDraw,Swap,FrameCompleted
0,1000000000,1001000000,0,0,0,0,0,0,0,0,0,0,1016000000
0,1020000000,1021000000,0,0,0,0,0,0,0,0,0,0,1035000000
0,1040000000,1041000000,0,0,0,0,0,0,0,0,0,0,1065000000
0,1070000000,1071000000,0,0,0,0,0,0,0,0,0,0,1082000000
0,1090000000,1091000000,0,0,0,0,0,0,0,0,0,0,1105000000
"""
        res = calculate_jank_metrics(sample_framestats, min_frames=3, refresh_rate_hz=60.0)
        self.assertNotIn("error", res)
        self.assertEqual(res["total_frames"], 5)
        self.assertGreater(res["p50_latency_ms"], 0)

if __name__ == "__main__":
    unittest.main()
