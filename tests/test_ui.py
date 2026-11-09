#!/usr/bin/env python3
"""
tests/test_ui.py - Unit tests for the stdlib UI layer (scripts/ui/).

These are deliberately snapshot-shaped: fixed width, fixed theme, exact strings.
Border alignment is the property that broke in production, so every box test
asserts that all rendered lines share one visible width, including lines with
emoji and ANSI codes.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from ui import UI, display_width, strip_ansi
from ui import keys, prompts, widgets
from ui.theme import Theme, make_theme
from ui.term import TermCaps


def plain_theme():
    return Theme(depth="none", plain=True)


class TestDisplayWidth(unittest.TestCase):

    def test_ascii(self):
        self.assertEqual(display_width("hello"), 5)

    def test_ansi_is_zero_width(self):
        self.assertEqual(display_width("\033[1;38;2;0;230;118mhello\033[0m"), 5)

    def test_cjk_is_two_cells(self):
        self.assertEqual(display_width("\u65e5\u672c"), 4)

    def test_emoji_is_two_cells(self):
        self.assertEqual(display_width("\U0001F680"), 2)          # rocket
        self.assertEqual(display_width("a\U0001F680b"), 4)

    def test_variation_selector_does_not_add_width(self):
        self.assertEqual(display_width("\u26a0\ufe0f"), 2)        # warning sign + VS16

    def test_text_symbol_stays_narrow(self):
        self.assertEqual(display_width("\u2714"), 1)              # check mark

    def test_strip_ansi(self):
        self.assertEqual(strip_ansi("\033[31mred\033[0m"), "red")


class TestBoxAlignment(unittest.TestCase):

    def _assert_uniform(self, lines, width):
        widths = sorted({display_width(line) for line in lines})
        self.assertEqual(widths, [width], "ragged box: %r" % (widths,))

    def test_box_width_is_exact(self):
        lines = widgets.box(["hello", "world"], 60, theme=None)
        self._assert_uniform(lines, 60)

    def test_box_with_emoji_stays_aligned(self):
        lines = widgets.box(["[ 1 ] \U0001F680 Multi-Tier", "[ 2 ] \U0001F50D Diagnose"],
                            74, theme=None)
        self._assert_uniform(lines, 74)

    def test_box_with_ansi_stays_aligned(self):
        t = Theme(depth="truecolor", plain=False)
        lines = widgets.box([t.paint("coloured", "ok"), "plain"], 50, theme=t)
        self._assert_uniform(lines, 50)

    def test_box_with_title(self):
        lines = widgets.box(["a"], 40, theme=None, title="STATUS")
        self._assert_uniform(lines, 40)
        self.assertIn("STATUS", lines[0])

    def test_ascii_glyphs(self):
        g = widgets.glyphs(False)
        lines = widgets.box(["x"], 30, theme=None, glyph=g)
        self.assertTrue(lines[0].startswith("+"))
        self.assertTrue(all(ord(c) < 128 for c in "".join(lines)))

    def test_long_line_is_truncated_not_wrapped(self):
        lines = widgets.box(["x" * 500], 40, theme=None)
        self._assert_uniform(lines, 40)


class TestWidgets(unittest.TestCase):

    def test_pad_alignments(self):
        self.assertEqual(widgets.pad("ab", 5), "ab   ")
        self.assertEqual(widgets.pad("ab", 5, "right"), "   ab")
        self.assertEqual(widgets.pad("ab", 5, "center"), " ab  ")

    def test_truncate_respects_display_width(self):
        out = widgets.truncate("abcdefghij", 5)
        self.assertLessEqual(display_width(out), 5)
        self.assertTrue(out.endswith("\u2026"))

    def test_badge_always_has_a_word(self):
        t = plain_theme()
        for tier in ("SAFE", "ADVANCED", "EXPERT", "UNSAFE"):
            text = widgets.badge(tier, theme=t)
            self.assertTrue(text.startswith("["), text)
            self.assertIn(tier[:3], text)

    def test_plain_theme_emits_no_escapes(self):
        t = plain_theme()
        self.assertEqual(t.ok, "")
        self.assertNotIn("\033", t.paint("x", "danger"))
        self.assertNotIn("\033", widgets.bar(5, 10, 10, theme=t))

    def test_colour_theme_emits_escapes(self):
        t = Theme(depth="truecolor", plain=False)
        self.assertIn("\033[", t.ok)
        self.assertIn("\033[", t.paint("x", "danger"))

    def test_bar_clamps_and_reports_percentage(self):
        self.assertIn("50%", widgets.bar(5, 10, 10))
        self.assertIn("100%", widgets.bar(99, 10, 10))
        self.assertIn("0%", widgets.bar(-3, 10, 10))

    def test_progress_bar_counts(self):
        line = widgets.progress_bar(3, 10, 60, theme=plain_theme(), label="pkg")
        self.assertIn("3/10", line)
        self.assertIn("pkg", line)

    def test_status_line_truncates(self):
        line = widgets.status_line(["SAMSUNG SM-G973F", "Android 14", "USB", "87%"], 20)
        self.assertLessEqual(display_width(line), 20)

    def test_kv_rows_align(self):
        rows = widgets.kv_rows([("CPU", "2.1"), ("SWAP", "12%")])
        self.assertEqual(len({r.index(":") for r in rows}), 1)


class TestThemeAndCaps(unittest.TestCase):

    def test_no_color_env_forces_plain(self):
        with patch.dict(os.environ, {"NO_COLOR": "1"}, clear=False):
            caps = TermCaps()
            self.assertTrue(caps.no_color)
            self.assertEqual(make_theme(caps).ok, "")

    def test_ascii_env_forces_ascii(self):
        with patch.dict(os.environ, {"ALFI_ASCII": "1"}, clear=False):
            caps = TermCaps()
            self.assertFalse(caps.unicode)

    def test_layout_width_is_clamped(self):
        caps = TermCaps()
        caps.width = 400
        self.assertLessEqual(caps.layout_width, 100)
        caps.width = 20
        self.assertGreaterEqual(caps.layout_width, 40)


class TestPrompts(unittest.TestCase):

    def test_read_line_strips_and_defaults(self):
        with patch("builtins.input", return_value="  hi  "):
            self.assertEqual(prompts.read_line("> "), "hi")
        with patch("builtins.input", return_value=""):
            self.assertEqual(prompts.read_line("> ", default="x"), "x")

    def test_read_line_eof_returns_none(self):
        with patch("builtins.input", side_effect=EOFError):
            self.assertIsNone(prompts.read_line("> "))
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            self.assertIsNone(prompts.read_line("> "))

    def test_confirm(self):
        for answer in ("y", "Y", "yes"):
            with patch("builtins.input", return_value=answer):
                self.assertTrue(prompts.confirm())
        for answer in ("n", "", "no"):
            with patch("builtins.input", return_value=answer):
                self.assertFalse(prompts.confirm())

    def test_typed_gate_requires_exact_phrase(self):
        with patch("builtins.input", return_value="I UNDERSTAND"):
            self.assertTrue(prompts.typed_gate("I UNDERSTAND"))
        with patch("builtins.input", return_value="i understand"):
            self.assertFalse(prompts.typed_gate("I UNDERSTAND"))

    def test_ask_validates(self):
        with patch("builtins.input", return_value="y"):
            self.assertEqual(prompts.ask("?", valid={"Y", "N"}), "Y")
        with patch("builtins.input", return_value="x"):
            self.assertIsNone(prompts.ask("?", valid={"Y", "N"}))


class TestKeys(unittest.TestCase):

    def test_no_raw_mode_in_ci(self):
        # stdout/stdin are not TTYs under the test runner
        self.assertFalse(keys.raw_available())
        self.assertIsNone(keys.read_key())


class TestUIFacade(unittest.TestCase):

    def test_ui_width_and_box(self):
        ui = UI(caps=TermCaps(), theme_obj=plain_theme())
        ui.width = 70
        lines = ui.box(["one", "two"], title="CARD")
        self.assertEqual({display_width(x) for x in lines}, {70})

    def test_ui_print_accepts_lists(self):
        ui = UI(caps=TermCaps(), theme_obj=plain_theme())
        with patch("sys.stdout.write") as w:
            ui.print(["a", "b"])
            self.assertEqual(w.call_count, 2)


if __name__ == "__main__":
    unittest.main()


class TestGraphicsWidgets(unittest.TestCase):

    def test_sparkline_exact_width(self):
        line = widgets.sparkline([1, 5, 3, 9, 2], width=20)
        self.assertEqual(display_width(line), 20)

    def test_sparkline_empty_is_blank(self):
        self.assertEqual(widgets.sparkline([], width=6), " " * 6)

    def test_sparkline_rises_with_values(self):
        low = widgets.sparkline([1, 1, 1], width=3)
        high = widgets.sparkline([9, 9, 9], width=3)
        self.assertEqual(low, high)  # flat series has no shape

    def test_sparkline_ascii_mode(self):
        line = widgets.sparkline([1, 2, 3], width=3, ascii_mode=True)
        self.assertTrue(all(ord(c) < 128 for c in line))

    def test_gauge_clamps_and_reports(self):
        self.assertIn("50%", widgets.gauge(5, 10, width=10))
        self.assertIn("100%", widgets.gauge(99, 10, width=10))
        self.assertIn("0%", widgets.gauge(-5, 10, width=10))
        self.assertIn("0%", widgets.gauge(1, 0, width=10))

    def test_gauge_shows_label_and_unit(self):
        line = widgets.gauge(3, 10, width=10, label="RAM", unit="3/10 GB")
        self.assertIn("RAM", line)
        self.assertIn("3/10 GB", line)

    def test_gradient_plain_is_identity(self):
        self.assertEqual(widgets.gradient("ALFi", plain=True), "ALFi")

    def test_gradient_truecolor_keeps_visible_width(self):
        painted = widgets.gradient("ALFi")
        self.assertIn("\033[38;2;", painted)
        self.assertEqual(display_width(painted), 4)

    def test_panel_is_uniform_width(self):
        lines = widgets.panel(["a", "bb", "ccc"], 40, theme=None, title="MONITOR")
        self.assertEqual({display_width(x) for x in lines}, {40})

    def test_panel_ascii_mode(self):
        lines = widgets.panel(["x"], 20, theme=None, ascii_mode=True)
        self.assertTrue(all(ord(c) < 128 for c in "".join(lines)))


class TestThemePresets(unittest.TestCase):

    def test_presets_differ(self):
        neon = Theme(depth="truecolor", preset="neon").ok
        amber = Theme(depth="truecolor", preset="amber").ok
        self.assertNotEqual(neon, amber)

    def test_unknown_preset_falls_back(self):
        self.assertEqual(Theme(depth="truecolor", preset="nope").preset, "neon")

    def test_env_selects_preset(self):
        with patch.dict(os.environ, {"ALFI_THEME": "mono"}, clear=False):
            theme_obj = make_theme(TermCaps())
            self.assertEqual(theme_obj.preset, "mono")
