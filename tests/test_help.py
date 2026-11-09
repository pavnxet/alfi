#!/usr/bin/env python3
"""
tests/test_help.py - the help system and the dashboard menu must not drift.

Two invariants:

1. every script with a main() is documented in helpdata AND reachable from the
   dashboard menu (a command nobody can find is a command that does not exist)
2. both help surfaces render from the same table, at the same width
"""

import os
import sys
import unittest
from unittest.mock import patch

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPTS)

import cli
import helpdata
import wizard
from ui import display_width
from ui.term import TermCaps
from ui.theme import Theme


def plain_ui(width=74):
    from ui import UI

    ui = UI(caps=TermCaps(), theme_obj=Theme(depth="none", plain=True))
    ui.width = width
    return ui


def script_names():
    """Scripts that expose a main() and are therefore commands."""
    names = set()
    for filename in os.listdir(SCRIPTS):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue
        with open(os.path.join(SCRIPTS, filename), encoding="utf-8") as handle:
            if "def main(" in handle.read():
                names.add(filename[:-3])
    return names


class TestCoverage(unittest.TestCase):

    def test_every_script_is_documented(self):
        """Every runnable script maps to a command that has a help entry."""
        module_to_command = {mod: cmd for cmd, mod in cli.COMMANDS.items() if mod}
        module_to_command["wizard"] = "tui"
        module_to_command["cli"] = "help"   # the dispatcher itself provides `alfi help`
        documented = {entry["name"] for entry in helpdata.COMMANDS}
        missing = []
        for module in script_names():
            command = module_to_command.get(module)
            if command is None:
                missing.append(module)          # not reachable from `alfi` at all
            elif command not in documented:
                missing.append("%s -> %s" % (module, command))
        self.assertEqual(missing, [], "undocumented or unreachable: %s" % sorted(missing))

    def test_every_menu_action_is_documented(self):
        documented = {entry["name"] for entry in helpdata.COMMANDS}
        aliases = {"ui_speed": "ui", "update_db": "update"}
        missing = []
        for key in wizard.ACTIONS_MAP:
            name = aliases.get(key, key)
            if name not in documented:
                missing.append(key)
        self.assertEqual(missing, [], "menu actions with no help: %s" % missing)


class TestMenuIntegrity(unittest.TestCase):

    def test_menu_covers_every_action(self):
        in_menu = {key for _, key in wizard.MENU_ORDER}
        self.assertEqual(set(wizard.ACTIONS_MAP) - in_menu, set())

    def test_menu_numbers_are_unique_and_contiguous(self):
        numbers = [num for num, _ in wizard.MENU_ORDER]
        self.assertEqual(len(numbers), len(set(numbers)))
        self.assertEqual(numbers, [str(i) for i in range(1, len(numbers) + 1)])

    def test_new_commands_are_present(self):
        for key in ("probe", "attrib", "verify", "watch"):
            self.assertIn(key, wizard.ACTIONS_MAP)
            self.assertIn(key, {k for _, k in wizard.MENU_ORDER})

    def test_every_action_points_at_a_real_script(self):
        for key, entry in wizard.ACTIONS_MAP.items():
            path = os.path.join(SCRIPTS, entry["script"])
            self.assertTrue(os.path.exists(path), "%s -> %s" % (key, entry["script"]))


class TestDataQuality(unittest.TestCase):

    def test_required_fields(self):
        for entry in helpdata.COMMANDS:
            for field in ("name", "group", "summary", "detail", "example", "mutates"):
                self.assertIn(field, entry, entry.get("name"))
            self.assertIn(entry["group"], helpdata.GROUPS, entry["name"])
            self.assertTrue(entry["summary"].strip())
            self.assertGreater(len(entry["detail"]), 40, entry["name"])
            self.assertIn("alfi", entry["example"], entry["name"])

    def test_names_unique(self):
        names = [entry["name"] for entry in helpdata.COMMANDS]
        self.assertEqual(len(names), len(set(names)))

    def test_mutation_flags_are_honest(self):
        """Anything that can change the phone must be marked."""
        mutating = {"modes", "optimize", "compile", "appops", "doze", "ui", "restore", "rescue"}
        for name in mutating:
            self.assertTrue(helpdata.by_name(name)["mutates"], name)
        for name in ("probe", "attrib", "verify", "bench", "status", "watch"):
            self.assertFalse(helpdata.by_name(name)["mutates"], name)

    def test_grouped_loses_nothing(self):
        grouped = sum(len(entries) for _, entries in helpdata.grouped())
        self.assertEqual(grouped, len(helpdata.COMMANDS))


class TestRendering(unittest.TestCase):

    def test_cli_help_lists_every_command(self):
        text = cli.render_help()
        for entry in helpdata.COMMANDS:
            self.assertIn(entry["name"], text)

    def test_detail_lines_wrap_to_width(self):
        lines = helpdata.detail_lines(helpdata.by_name("probe"), width=60)
        self.assertTrue(all(display_width(line) <= 60 for line in lines))
        self.assertIn("example: alfi probe", lines)

    def test_help_command_known(self):
        with patch("sys.stdout"):
            self.assertEqual(cli.help_command(["probe"]), 0)

    def test_help_command_unknown_suggests(self):
        with patch("sys.stdout"), patch("sys.stderr"):
            self.assertEqual(cli.help_command(["proxx"]), 2)

    def test_dashboard_help_screen_is_uniform(self):
        with patch.object(wizard, "get_ui", return_value=plain_ui(74)):
            with patch("sys.stdout"):
                wizard.print_help_screen()

    def test_dashboard_help_screen_box_width(self):
        ui = plain_ui(74)
        captured = []
        ui.print = lambda *lines: captured.extend(
            l for line in lines for l in (line if isinstance(line, (list, tuple)) else [line]))
        with patch.object(wizard, "get_ui", return_value=ui):
            wizard.print_help_screen()
        self.assertEqual({display_width(line) for line in captured}, {74})

    def test_unknown_command_help_returns_false(self):
        with patch.object(wizard, "get_ui", return_value=plain_ui(74)), patch("sys.stdout"):
            self.assertFalse(wizard.print_command_help("nope"))
            self.assertTrue(wizard.print_command_help("probe"))


if __name__ == "__main__":
    unittest.main()
