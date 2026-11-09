#!/usr/bin/env python3
"""
tests/test_probe.py - PSI / thermal / memory parsing for `alfi probe`.

Fixtures are verbatim shapes of the real dumps, because the class of bug this
project keeps hitting is "the parser matched a fixture the device never emits".
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import probe
from ui import display_width
from ui.term import TermCaps
from ui.theme import Theme

PSI_BLOCK = [
    "some avg10=3.42 avg60=1.85 avg300=0.94 total=81234567",
    "full avg10=1.10 avg60=0.42 avg300=0.11 total=9876543",
]
THERMAL_BLOCK = [
    "IsStatusOverride: false",
    "Thermal Status: 1",
    "Cached temperatures:",
    "  Temperature{mValue=32.5, mType=2, mName=battery, mStatus=0}",
    "  Temperature{mValue=41.2, mType=0, mName=AP, mStatus=1}",
    "HAL Ready: true",
]
MEM_BLOCK = [
    "MemTotal:        7432112 kB",
    "MemAvailable:    1204332 kB",
    "SwapTotal:       2097152 kB",
    "SwapFree:        1572864 kB",
]
BATTERY_BLOCK = ["  level: 87", "  temperature: 312"]


def plain_ui(width=74):
    from ui import UI

    ui = UI(caps=TermCaps(), theme_obj=Theme(depth="none", plain=True))
    ui.width = width
    return ui


class TestPsi(unittest.TestCase):

    def test_parses_both_lines(self):
        psi = probe.parse_psi(PSI_BLOCK)
        self.assertAlmostEqual(psi["some"]["avg60"], 1.85)
        self.assertAlmostEqual(psi["full"]["avg60"], 0.42)
        self.assertEqual(psi["some"]["total"], 81234567.0)

    def test_unavailable_returns_empty(self):
        self.assertEqual(probe.parse_psi(["unavailable"]), {})
        self.assertEqual(probe.parse_psi([]), {})

    def test_cpu_has_no_full_line(self):
        psi = probe.parse_psi(["some avg10=2.10 avg60=1.50 avg300=1.20 total=55555"])
        self.assertIn("some", psi)
        self.assertNotIn("full", psi)


class TestVerdict(unittest.TestCase):

    def test_ladder(self):
        cases = [
            (0.5, 0.0, "memory is not the problem"),
            (3.0, 0.2, "mild pressure"),
            (12.0, 1.0, "real stutter source"),
            (25.0, 2.0, "severe pressure"),
            (10.0, 7.0, "thrashing"),
        ]
        for some, full, expected in cases:
            self.assertEqual(probe.verdict(some, full)[0], expected,
                             "some=%s full=%s" % (some, full))


class TestThermal(unittest.TestCase):

    def test_status_and_hottest(self):
        thermal = probe.parse_thermal(THERMAL_BLOCK)
        self.assertEqual(thermal["status"], 1)
        self.assertEqual(thermal["status_name"], "LIGHT")
        self.assertFalse(thermal["override"])
        self.assertEqual(thermal["hottest"][0], ("AP", 41.2))

    def test_override_is_flagged(self):
        block = ["IsStatusOverride: true", "Thermal Status: 3"]
        self.assertTrue(probe.parse_thermal(block)["override"])

    def test_nan_zone_ignored(self):
        block = ["Thermal Status: 0",
                 "  Temperature{mValue=NaN, mType=0, mName=AP, mStatus=0}"]
        self.assertEqual(probe.parse_thermal(block)["hottest"], [])

    def test_unknown_status_is_not_rounded_up(self):
        self.assertEqual(probe.parse_thermal(["Thermal Status: 9"])["status_name"], "UNKNOWN")


class TestMemoryAndBattery(unittest.TestCase):

    def test_mem_percentages(self):
        mem = probe.parse_mem(MEM_BLOCK)
        self.assertAlmostEqual(mem["used_pct"], 83.8, places=1)
        self.assertAlmostEqual(mem["swap_pct"], 25.0, places=1)

    def test_battery_tenths_of_a_degree(self):
        self.assertEqual(probe.parse_battery(BATTERY_BLOCK)["temp_c"], 31.2)

    def test_vmstat_fallback(self):
        vm = probe.parse_vmstat(["pswpin 120", "pswpout 340", "garbage line"])
        self.assertEqual(vm["pswpin"], 120)
        self.assertNotIn("garbage", vm)


class TestSections(unittest.TestCase):

    def test_split_keeps_full_header(self):
        raw = "@@PSI memory\nsome avg10=1.0 avg60=1.0 avg300=1.0 total=1\n@@MEM\nMemTotal: 1 kB"
        sections = probe.split_sections(raw)
        self.assertIn("PSI memory", sections)
        self.assertIn("MEM", sections)


class TestProbeAndRender(unittest.TestCase):

    RAW = ("@@PSI memory\n" + "\n".join(PSI_BLOCK) + "\n"
           "@@PSI io\nsome avg10=0.2 avg60=0.1 avg300=0.0 total=1\n"
           "@@PSI cpu\nsome avg10=2.1 avg60=1.5 avg300=1.2 total=2\n"
           "@@VMSTAT\npswpin 120\n"
           "@@THERMAL\n" + "\n".join(THERMAL_BLOCK) + "\n"
           "@@BATTERY\n" + "\n".join(BATTERY_BLOCK) + "\n"
           "@@MEM\n" + "\n".join(MEM_BLOCK))

    def test_probe_end_to_end(self):
        with patch("connect.run_adb", return_value=(True, self.RAW)):
            data = probe.probe()
        self.assertTrue(data["psi_supported"])
        self.assertEqual(data["memory_verdict"], "mild pressure")
        self.assertEqual(data["thermal"]["status_name"], "LIGHT")
        self.assertEqual(data["battery"]["level"], 87)

    def test_probe_error(self):
        with patch("connect.run_adb", return_value=(False, "device offline")):
            self.assertIn("error", probe.probe())

    def test_render_is_uniform_width(self):
        with patch("connect.run_adb", return_value=(True, self.RAW)):
            data = probe.probe()
        lines = probe.render(plain_ui(74), data, width=74)
        self.assertEqual({display_width(x) for x in lines}, {74})

    def test_render_without_psi_shows_fallback(self):
        raw = self.RAW.replace("@@PSI memory\n" + "\n".join(PSI_BLOCK), "@@PSI memory\nunavailable")
        with patch("connect.run_adb", return_value=(True, raw)):
            data = probe.probe()
        text = "\n".join(probe.render(plain_ui(74), data, width=74))
        self.assertIn("PSI unavailable", text)
        self.assertIn("swap in/out", text)


if __name__ == "__main__":
    unittest.main()
