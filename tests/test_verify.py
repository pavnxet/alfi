#!/usr/bin/env python3
"""
tests/test_verify.py - post-reboot verification (the Canta failure mode).

`alfi verify` exists because a debloater that reports success and never looks
again is how users end up with apps silently restored by an OEM update.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import verify
from ui import display_width
from ui.term import TermCaps
from ui.theme import Theme


def plain_ui(width=74):
    from ui import UI

    ui = UI(caps=TermCaps(), theme_obj=Theme(depth="none", plain=True))
    ui.width = width
    return ui


class TestClassify(unittest.TestCase):

    def test_held(self):
        self.assertEqual(verify.classify("applied", "disabled"), "held")

    def test_came_back(self):
        self.assertEqual(verify.classify("applied", "enabled"), "came back")
        self.assertEqual(verify.classify("applied", "uninstalled"), "came back")

    def test_gone_and_unknown(self):
        self.assertEqual(verify.classify("applied", "not_found"), "gone")
        self.assertEqual(verify.classify("applied", "invalid"), "unknown")


class TestManifestParsing(unittest.TestCase):

    def _write(self, payload):
        handle, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        self.addCleanup(os.remove, path)
        return path

    def test_mode_manifest_dict(self):
        path = self._write({"packages": {"a.b": {"status": "applied"}}})
        self.assertEqual(verify.manifest_packages(path), [("a.b", "applied")])

    def test_restore_manifest_list(self):
        path = self._write({"packages": ["a.b", "c.d"]})
        self.assertEqual(verify.manifest_packages(path), [("a.b", "applied"), ("c.d", "applied")])

    def test_legacy_disabled_packages_key(self):
        path = self._write({"disabled_packages": ["x.y"]})
        self.assertEqual(verify.manifest_packages(path), [("x.y", "applied")])


class TestCheck(unittest.TestCase):

    def test_mixed_results(self):
        handle, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            json.dump({"packages": {"a.b": {}, "c.d": {}}}, f)
        self.addCleanup(os.remove, path)

        def fake_state(pkg, **kwargs):
            return "disabled" if pkg == "a.b" else "enabled"

        with patch("verify.get_package_state", side_effect=fake_state):
            results = verify.check(path)
        verdicts = {r["package"]: r["verdict"] for r in results}
        self.assertEqual(verdicts, {"a.b": "held", "c.d": "came back"})


class TestBaseline(unittest.TestCase):

    def test_writes_boot_id_and_states(self):
        with patch("verify.latest_manifest", return_value=None), \
             patch("verify.read_boot_id", return_value="boot-123"), \
             patch.object(verify, "BACKUPS", tempfile.mkdtemp()):
            path, payload = verify.write_baseline()
        self.addCleanup(os.remove, path)
        self.assertEqual(payload["boot_id"], "boot-123")
        with open(path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["boot_id"], "boot-123")


class TestRender(unittest.TestCase):

    def test_uniform_width_and_flags_restored(self):
        results = [
            {"package": "a.b", "recorded": "applied", "current": "disabled", "verdict": "held"},
            {"package": "c.d", "recorded": "applied", "current": "enabled", "verdict": "came back"},
        ]
        lines = verify.render(plain_ui(74), results, width=74)
        self.assertEqual({display_width(x) for x in lines}, {74})
        text = "\n".join(lines)
        self.assertIn("1 of 2", text)
        self.assertIn("came back: c.d", text)

    def test_empty_manifest_message(self):
        lines = verify.render(plain_ui(74), [], width=74)
        self.assertIn("no manifest", "\n".join(lines))


if __name__ == "__main__":
    unittest.main()
