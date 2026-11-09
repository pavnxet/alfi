#!/usr/bin/env python3
"""
tests/test_attrib.py - runaway processes, dexopt state and wakeup parsing.

The wakeup parser is deliberately best-effort: `dumpsys alarm` changes shape
between OEMs and versions, so the contract tested here is "either correct
numbers or an honest 'unavailable'", never a confident zero.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import attrib
from ui import display_width
from ui.term import TermCaps
from ui.theme import Theme

PS_BLOCK = [
    "  PID   RSS NAME",
    " 1234 812340 com.android.settings",
    " 2345 145000 com.android.systemui",
    " 3456  98000 com.facebook.katana",
]

DEXOPT_BLOCK = [
    "Packages:",
    "  com.android.settings:",
    "    [status=speed-profile] [reason=bg-dexopt] [primary-abi=arm64-v8a]",
    "  com.facebook.katana:",
    "    [status=verify] [reason=install] [primary-abi=arm64-v8a]",
    "  com.whatsapp:",
    "    [status=speed] [reason=cmdline] [primary-abi=arm64-v8a]",
]

ALARM_BLOCK = [
    "    +1h32m12s running, 124 wakeups: +1h32m12s com.facebook.katana",
    "    +2h10m00s running, 42 wakeups: +2h10m00s com.miui.analytics",
]


def plain_ui(width=74):
    from ui import UI

    ui = UI(caps=TermCaps(), theme_obj=Theme(depth="none", plain=True))
    ui.width = width
    return ui


class TestProcesses(unittest.TestCase):

    def test_parses_and_sorts_by_rss(self):
        rows = attrib.parse_ps(PS_BLOCK)
        self.assertEqual(rows[0]["name"], "com.android.settings")
        self.assertAlmostEqual(rows[0]["rss_mb"], 793.3, places=1)
        self.assertEqual([r["rss_mb"] for r in rows], sorted([r["rss_mb"] for r in rows], reverse=True))

    def test_header_and_garbage_ignored(self):
        rows = attrib.parse_ps(["  PID   RSS NAME", "not a row", ""])
        self.assertEqual(rows, [])

    def test_runaway_threshold_is_relative_to_ram(self):
        rows = attrib.parse_ps(PS_BLOCK)
        # 8 GB device -> 25% = 2048 MB, so nothing is flagged
        self.assertEqual(attrib.flag_runaways(rows, total_gb=8.0), [])
        # 2 GB device -> 512 MB limit, so the 793 MB process is flagged
        flagged = attrib.flag_runaways(rows, total_gb=2.0)
        self.assertEqual(len(flagged), 1)
        self.assertIn("793", flagged[0]["reason"])


class TestDexopt(unittest.TestCase):

    def test_counts_and_statuses(self):
        data = attrib.parse_dexopt(DEXOPT_BLOCK)
        self.assertEqual(data["counts"]["verify"], 1)
        self.assertEqual(data["counts"]["speed"], 1)
        self.assertEqual(data["packages"]["com.whatsapp"]["status"], "speed")

    def test_reason_captured(self):
        data = attrib.parse_dexopt(DEXOPT_BLOCK)
        self.assertEqual(data["packages"]["com.android.settings"]["reason"], "bg-dexopt")

    def test_empty_is_empty(self):
        self.assertEqual(attrib.parse_dexopt([])["packages"], {})


class TestAlarms(unittest.TestCase):

    def test_parses_wakeups(self):
        rows = attrib.parse_alarms(ALARM_BLOCK)
        self.assertEqual(rows[0]["package"], "com.facebook.katana")
        self.assertEqual(rows[0]["wakeups"], 124)

    def test_unknown_format_is_empty_not_zero(self):
        self.assertEqual(attrib.parse_alarms(["some other dump shape"]), [])


class TestCollectAndRender(unittest.TestCase):

    RAW = ("@@PS\n" + "\n".join(PS_BLOCK) + "\n"
           "@@DEXOPT\n" + "\n".join(DEXOPT_BLOCK) + "\n"
           "@@ALARM\n" + "\n".join(ALARM_BLOCK))

    def test_collect_end_to_end(self):
        with patch("connect.run_adb", return_value=(True, self.RAW)):
            data = attrib.collect()
        self.assertEqual(len(data["runaways"]), 1)
        self.assertTrue(data["alarms_available"])
        self.assertEqual(data["dexopt"]["counts"]["verify"], 1)

    def test_error_path(self):
        with patch("connect.run_adb", return_value=(False, "offline")):
            self.assertIn("error", attrib.collect())

    def test_render_uniform_width(self):
        with patch("connect.run_adb", return_value=(True, self.RAW)):
            data = attrib.collect()
        lines = attrib.render(plain_ui(74), data, width=74)
        self.assertEqual({display_width(x) for x in lines}, {74})

    def test_render_states_unavailable_instead_of_zero(self):
        raw = "@@PS\n  PID RSS NAME\n@@DEXOPT\n@@ALARM\n"
        with patch("connect.run_adb", return_value=(True, raw)):
            data = attrib.collect()
        text = "\n".join(attrib.render(plain_ui(74), data, width=74))
        self.assertIn("unavailable", text)
        self.assertNotIn("0 wakeups", text)


if __name__ == "__main__":
    unittest.main()
