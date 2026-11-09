#!/usr/bin/env python3
"""
tests/test_diagnose.py - Unit Tests for Deep Performance & Lag Diagnostic Engine

Tests CPU load, memory parsing, swap/zRAM pressure detection, and diagnostic report formatting.
"""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from diagnose import check_cpu_and_load, check_memory_and_swap

class TestDiagnose(unittest.TestCase):

    @patch("diagnose.run_adb")
    def test_check_cpu_and_load_parsing(self, mock_adb):
        """Test parsing of /proc/loadavg and dumpsys cpuinfo output."""
        def adb_side_effect(args, timeout=10):
            if "cat /proc/loadavg" in " ".join(args):
                return True, "4.25 3.10 2.80 3/1024 15420"
            elif "dumpsys cpuinfo" in " ".join(args):
                sample_cpu = (
                    "Load: 4.25 / 3.10 / 2.80\n"
                    "CPU usage from 5000ms to 0ms ago:\n"
                    "  35% 1234/system_server: 20% user + 15% kernel\n"
                    "  28% 5678/com.google.android.gms: 22% user + 6% kernel\n"
                    "  12% 9999/com.facebook.katana: 10% user + 2% kernel\n"
                    "95% TOTAL: 60% user + 35% kernel\n"
                )
                return True, sample_cpu
            return False, ""

        mock_adb.side_effect = adb_side_effect

        load_avg, total_cpu_line, top_procs = check_cpu_and_load()
        self.assertEqual(load_avg, ["4.25", "3.10", "2.80"])
        self.assertIn("95% TOTAL:", total_cpu_line)
        self.assertEqual(len(top_procs), 3)
        self.assertEqual(top_procs[0]["name"], "system_server")
        self.assertEqual(top_procs[0]["pct"], "35%")
        self.assertEqual(top_procs[1]["name"], "com.google.android.gms")

    @patch("diagnose.run_adb")
    def test_check_memory_and_swap_parsing(self, mock_adb):
        """Test parsing of /proc/meminfo and zRAM usage calculation."""
        sample_meminfo = (
            "MemTotal:        3932160 kB\n"
            "MemFree:          250000 kB\n"
            "MemAvailable:     950000 kB\n"
            "Buffers:           45000 kB\n"
            "Cached:           700000 kB\n"
            "SwapTotal:       2097152 kB\n"
            "SwapFree:        1048576 kB\n"
        )
        mock_adb.return_value = (True, sample_meminfo)

        mem_stats = check_memory_and_swap()
        self.assertAlmostEqual(mem_stats["total_ram_mb"], 3840.0, places=1)
        self.assertAlmostEqual(mem_stats["avail_ram_mb"], 927.7, places=1)
        self.assertAlmostEqual(mem_stats["swap_total_mb"], 2048.0, places=1)
        self.assertAlmostEqual(mem_stats["swap_used_mb"], 1024.0, places=1)

if __name__ == "__main__":
    unittest.main()
