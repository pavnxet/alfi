#!/usr/bin/env python3
"""
tests/test_monitor.py - the `alfi watch` live monitor.

Parsing is tested against one realistic combined ADB blob; rendering is tested
for width; main() is tested in non-TTY mode, where it must print exactly one
snapshot and exit instead of looping.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import monitor
from ui import display_width
from ui.term import TermCaps
from ui.theme import Theme

BLOB = """2.31 2.10 1.95
MemTotal:        7432112 kB
MemAvailable:    1204332 kB
SwapTotal:       2097152 kB
SwapFree:        1572864 kB
  level: 87
  temperature: 312
  23% 1234/com.android.systemui: 12% user + 11% kernel
"""


def plain_ui():
    from ui import UI

    ui = UI(caps=TermCaps(), theme_obj=Theme(depth="none", plain=True))
    ui.width = 74
    return ui


class TestSnapshot(unittest.TestCase):

    def test_parses_all_fields(self):
        with patch("connect.run_adb", return_value=(True, BLOB)):
            snap = monitor.snapshot()
        self.assertEqual(snap["load"][0], 2.31)
        self.assertEqual(snap["battery"], 87)
        self.assertEqual(snap["temp_c"], 31.2)
        self.assertAlmostEqual(snap["mem_pct"], 83.8, places=1)
        self.assertAlmostEqual(snap["swap_pct"], 25.0, places=1)
        self.assertIn("systemui", snap["top"])

    def test_error_path(self):
        with patch("connect.run_adb", return_value=(False, "device offline")):
            self.assertIn("error", monitor.snapshot())


class TestRender(unittest.TestCase):

    def test_panel_lines_share_one_width(self):
        with patch("connect.run_adb", return_value=(True, BLOB)):
            snap = monitor.snapshot()
        lines = monitor.render(plain_ui(), snap, [2.0, 2.3, 2.1], width=74)
        self.assertEqual({display_width(x) for x in lines}, {74})

    def test_error_snapshot_renders_a_message(self):
        lines = monitor.render(plain_ui(), {"error": "no device"}, [], width=60)
        self.assertEqual({display_width(x) for x in lines}, {60})
        self.assertIn("unreachable", "\n".join(lines))


class TestMain(unittest.TestCase):

    def test_non_tty_prints_once_and_exits(self):
        with patch("connect.run_adb", return_value=(True, BLOB)), \
             patch.object(monitor, "get_ui", return_value=plain_ui()), \
             patch("sys.stdout"):
            self.assertEqual(monitor.main([]), 0)

    def test_json_mode(self):
        with patch("connect.run_adb", return_value=(True, BLOB)), \
             patch.object(monitor, "get_ui", return_value=plain_ui()), \
             patch("sys.stdout") as out:
            self.assertEqual(monitor.main(["--json"]), 0)
            printed = "".join(call[0][0] for call in out.write.call_args_list)
            self.assertIn('"battery": 87', printed)


if __name__ == "__main__":
    unittest.main()
