#!/usr/bin/env python3
"""
tests/test_cli.py - the `alfi` dispatcher and persisted defaults.

The important assertion here is reachability: every script in scripts/ must be
invocable as `alfi <command>`, because "fully usable from the terminal" is the
whole point of the dispatcher.
"""

import os
import sys
import types
import unittest
from unittest.mock import patch

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPTS)

import cli
import config


class TestReachability(unittest.TestCase):

    def test_every_script_has_a_command(self):
        skip = {"__init__", "cli", "config", "wizard"}  # wizard is `alfi` itself
        scripts = set()
        for name in os.listdir(SCRIPTS):
            if not name.endswith(".py") or name.startswith("_"):
                continue
            with open(os.path.join(SCRIPTS, name), encoding="utf-8") as fh:
                if "def main(" not in fh.read():
                    continue  # library module (operations, errors) - not a command
            scripts.add(name[:-3])
        reachable = {m for m in cli.COMMANDS.values() if m}
        missing = scripts - skip - reachable
        self.assertEqual(missing, set(), "not reachable via `alfi`: %s" % sorted(missing))

    def test_command_table_targets_existing_modules(self):
        for command, module_name in cli.COMMANDS.items():
            if module_name is None:
                continue
            self.assertTrue(
                os.path.exists(os.path.join(SCRIPTS, module_name + ".py")),
                "%s -> missing %s.py" % (command, module_name),
            )


class TestDispatch(unittest.TestCase):

    def setUp(self):
        self.captured = {}
        fake = types.ModuleType("fake_module")

        def main():
            self.captured["argv"] = list(sys.argv)
            return 0

        fake.main = main
        sys.modules["fake_module"] = fake

    def tearDown(self):
        sys.modules.pop("fake_module", None)

    def test_argv_is_rewritten_and_restored(self):
        before = list(sys.argv)
        rc = cli.dispatch("fake_module", ["--json"], {})
        self.assertEqual(rc, 0)
        self.assertEqual(self.captured["argv"], ["fake_module", "--json"])
        self.assertEqual(sys.argv, before)

    def test_saved_mode_is_injected_for_modes(self):
        argv = cli.with_defaults("modes", [], {"mode": "medium"})
        self.assertEqual(argv, ["--mode", "medium"])

    def test_explicit_flag_beats_saved_default(self):
        argv = cli.with_defaults("modes", ["--mode", "low"], {"mode": "medium"})
        self.assertEqual(argv.count("--mode"), 1)
        self.assertIn("low", argv)

    def test_defaults_not_injected_for_other_commands(self):
        self.assertEqual(cli.with_defaults("diagnose", [], {"mode": "medium"}), [])


class TestEntry(unittest.TestCase):

    def test_bare_alfi_opens_the_dashboard(self):
        with patch.object(cli, "dispatch", return_value=0) as d:
            self.assertEqual(cli.main([]), 0)
            self.assertEqual(d.call_args[0][0], "wizard")

    def test_unknown_command_exits_2(self):
        with patch("sys.stderr"):
            self.assertEqual(cli.main(["nope"]), 2)

    def test_help_exits_0(self):
        with patch("sys.stdout"):
            self.assertEqual(cli.main(["--help"]), 0)


class TestStatus(unittest.TestCase):

    def test_no_device_returns_nonzero_when_unauthorised(self):
        with patch("connect.get_connected_devices",
                   return_value=[{"serial": "X", "status": "unauthorized"}]), \
             patch("ui.ui"):
            self.assertEqual(cli.status([]), 1)

    def test_authorised_device_prints_one_line(self):
        info = {"brand": "samsung", "model": "SM-G973F",
                "android_version": "14", "sdk_level": "34"}
        with patch("connect.get_connected_devices",
                   return_value=[{"serial": "USB1", "status": "device"}]), \
             patch("connect.get_device_info", return_value=info), \
             patch("connect.run_adb", return_value=(True, "  level: 87")), \
             patch("ui.ui") as u:
            self.assertEqual(cli.status([]), 0)
            u.return_value.print.assert_called()


class TestConfig(unittest.TestCase):

    def setUp(self):
        self.tmp = os.path.join(os.path.dirname(__file__), "_cfg_test.json")
        self.env = patch.dict(os.environ, {"ALFI_CONFIG": self.tmp}, clear=False)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        if os.path.exists(self.tmp):
            os.remove(self.tmp)

    def test_defaults_when_missing(self):
        self.assertEqual(config.load()["color"], "auto")

    def test_round_trip(self):
        ok, _ = config.set_value("mode", "high")
        self.assertTrue(ok)
        self.assertEqual(config.load()["mode"], "high")

    def test_unknown_key_rejected(self):
        ok, message = config.set_value("nope", "1")
        self.assertFalse(ok)
        self.assertIn("unknown key", message)

    def test_bool_coercion(self):
        config.set_value("ascii", "yes")
        self.assertIs(config.load()["ascii"], True)

    def test_int_coercion_and_validation(self):
        self.assertTrue(config.set_value("user", "10")[0])
        self.assertEqual(config.load()["user"], 10)
        self.assertFalse(config.set_value("user", "ten")[0])

    def test_env_projection(self):
        data = config.load()
        data.update({"device": "1.2.3.4:5555", "color": "never", "ascii": True})
        config.apply_to_env(data)
        self.assertEqual(os.environ.get("ANDROID_SERIAL"), "1.2.3.4:5555")
        self.assertEqual(os.environ.get("NO_COLOR"), "1")
        self.assertEqual(os.environ.get("ALFI_ASCII"), "1")


if __name__ == "__main__":
    unittest.main()
