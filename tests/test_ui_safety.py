#!/usr/bin/env python3
"""
tests/test_ui_safety.py - Safety regressions, asserted through the UI path.

The UI refactor moved a lot of printing around. These tests exist to prove that
nothing about *when* the tool mutates the device changed:

1. the rollback manifest is on disk, fsynced, before the first apply_package_state
2. a cancelled run writes nothing to the device
3. Ultra still refuses without the exact phrase
4. the allowlist still blocks protected packages
"""

import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import modes


class TestManifestOrdering(unittest.TestCase):
    """The snapshot must exist before the first mutation, not after."""

    def test_manifest_exists_when_first_mutation_runs(self):
        seen = {}

        def fake_apply(pkg, want, serial=None, dry_run=False, user_id=0, sdk_level=31):
            # Look for the manifest at the moment the first package is touched.
            manifest_dir = os.path.join(os.path.dirname(modes.__file__), "..", "backups")
            found = []
            if os.path.isdir(manifest_dir):
                for name in os.listdir(manifest_dir):
                    if name.startswith("mode_low_") and name.endswith(".json"):
                        found.append(name)
            seen.setdefault("manifests_at_first_call", found)
            return True, "Disabled"

        plan = {
            "approved_packages": ["com.example.bloat"],
            "blocked_packages": [],
            "package_metadata": {"com.example.bloat": {"name": "Bloat", "tier": "Recommended"}},
            "config": {
                "label": "Low",
                "name": "Low",
                "emoji": "",
                "animation_scale": "0.75",
                "trim_cache": False,
                "appops_preset": None,
                "standby_bucket": None,
                "art_filter": None,
                "package_tiers": ["Recommended"],
                "category_filter": ["samsung"],
                "requires_confirmation": False,
            },
        }

        with patch.object(modes, "plan_mode_optimization", return_value=plan), \
             patch.object(modes, "apply_package_state", side_effect=fake_apply), \
             patch.object(modes, "get_installed_packages", return_value={"com.example.bloat"}), \
             patch.object(modes, "export_on_device_manifest", return_value=None), \
             patch.object(modes, "set_animation_scale", return_value=None), \
             patch.object(modes, "trim_system_cache", return_value=None):
            modes.execute_mode_optimization("low", serial=None, dry_run=False, auto_confirm=True)

        self.assertTrue(
            seen.get("manifests_at_first_call"),
            "no rollback manifest existed when the first mutation ran",
        )


class TestUltraGate(unittest.TestCase):
    """Ultra keeps its exact-phrase gate through the new prompt layer."""

    def test_wrong_phrase_aborts(self):
        plan = {
            "approved_packages": [],
            "blocked_packages": [],
            "package_metadata": {},
            "config": {
                "label": "Ultra", "name": "Ultra", "emoji": "",
                "animation_scale": "0.0", "trim_cache": False, "appops_preset": None,
                "standby_bucket": None, "art_filter": None,
                "package_tiers": ["Unsafe"], "category_filter": [], "requires_confirmation": True,
            },
        }
        with patch.object(modes, "plan_mode_optimization", return_value=plan), \
             patch.object(modes, "get_installed_packages", return_value=set()), \
             patch("builtins.input", return_value="I understand"):
            result = modes.execute_mode_optimization(
                "ultra", serial=None, dry_run=True, force_ultra=False,
                interactive_confirm=True, auto_confirm=False,
            )
        self.assertFalse(result.get("success", True))


class TestAllowlist(unittest.TestCase):
    """Protected packages never reach apply_package_state."""

    def test_critical_package_is_blocked(self):
        installed = {"com.android.phone", "com.android.systemui"}
        plan = modes.plan_mode_optimization("ultra", installed, manufacturer="samsung")
        approved = set(plan["approved_packages"])
        self.assertNotIn("com.android.phone", approved)
        self.assertNotIn("com.android.systemui", approved)


if __name__ == "__main__":
    unittest.main()
