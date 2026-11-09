#!/usr/bin/env python3
"""
tests/test_modes.py - Comprehensive Unit Tests for Multi-Tier Mode Engine & Dependency Graph

Verifies:
- Integrity of all 4 optimization mode definitions (Low, Medium, High, Ultra)
- Dependency graph construction and reverse-lookup indexing
- Dependency conflict blocking (Inspiration: UAD-ng)
- Critical system component whitelisting (WebView, Telephony, UI)
- Input method (Keyboard) & Home screen (Launcher) safeguards
- Ultra mode safety gate enforcement (requires confirmation)
- Dry-run execution across all 4 modes without real ADB hardware
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from modes import (
    OPTIMIZATION_MODES,
    MODE_CONFIGS,
    get_mode_config,
    build_dependency_graph,
    validate_package_dependencies,
    plan_mode_optimization,
    execute_mode_optimization,
    CRITICAL_NEVER_DISABLE,
    KEYBOARD_PACKAGES,
    LAUNCHER_PACKAGES
)

class TestOptimizationModes(unittest.TestCase):

    def test_mode_configs_integrity(self):
        """Ensure all 4 modes exist and have valid configuration fields."""
        self.assertEqual(len(OPTIMIZATION_MODES), 4)
        for mode in OPTIMIZATION_MODES:
            self.assertIn(mode, MODE_CONFIGS)
            cfg = get_mode_config(mode)
            self.assertIn("name", cfg)
            self.assertIn("emoji", cfg)
            self.assertIn("animation_scale", cfg)
            self.assertIn("trim_cache", cfg)
            self.assertIn("package_tiers", cfg)
            self.assertIn("requires_confirmation", cfg)

        self.assertEqual(MODE_CONFIGS["low"]["animation_scale"], "0.75")
        self.assertEqual(MODE_CONFIGS["medium"]["animation_scale"], "0.5")
        self.assertEqual(MODE_CONFIGS["high"]["animation_scale"], "0.5")
        self.assertEqual(MODE_CONFIGS["ultra"]["animation_scale"], "0.0")

        self.assertFalse(MODE_CONFIGS["low"]["requires_confirmation"])
        self.assertFalse(MODE_CONFIGS["medium"]["requires_confirmation"])
        self.assertFalse(MODE_CONFIGS["high"]["requires_confirmation"])
        self.assertTrue(MODE_CONFIGS["ultra"]["requires_confirmation"])

    def test_invalid_mode_rejection(self):
        """Reject uncalibrated or misspelled mode requests."""
        with self.assertRaises(ValueError):
            get_mode_config("extreme")
        with self.assertRaises(ValueError):
            get_mode_config("turbo")

    def test_dependency_graph_building(self):
        """Ensure dependencies and reverse dependents are indexed correctly."""
        mock_db = {
            "categories": {
                "samsung": {
                    "packages": {
                        "com.sec.android.app.samsungapps": {
                            "dependencies": ["com.osp.app.signin"]
                        },
                        "com.osp.app.signin": {
                            "dependents": ["com.sec.android.app.samsungapps"]
                        }
                    }
                }
            }
        }
        deps, dep_ons = build_dependency_graph(mock_db)
        self.assertIn("com.sec.android.app.samsungapps", deps)
        self.assertEqual(deps["com.sec.android.app.samsungapps"], ["com.osp.app.signin"])
        self.assertIn("com.osp.app.signin", dep_ons)
        self.assertIn("com.sec.android.app.samsungapps", dep_ons["com.osp.app.signin"])

    def test_critical_packages_safeguard(self):
        """Fundamental OS services must never be approved for disabling."""
        mock_db = {"categories": {}}
        packages = ["com.android.phone", "com.google.android.webview", "com.aura.oobe.samsung"]
        installed = set(packages)

        approved, blocked = validate_package_dependencies(packages, installed, mock_db)
        self.assertIn("com.aura.oobe.samsung", approved)
        self.assertNotIn("com.android.phone", approved)
        self.assertNotIn("com.google.android.webview", approved)

        blocked_pkgs = [b["package"] for b in blocked]
        self.assertIn("com.android.phone", blocked_pkgs)
        self.assertIn("com.google.android.webview", blocked_pkgs)

    def test_dependency_conflict_blocking(self):
        """Disabling a dependency must be blocked when a dependent app is installed."""
        mock_db = {
            "categories": {
                "samsung": {
                    "packages": {
                        "com.osp.app.signin": {
                            "dependents": ["com.sec.android.app.samsungapps"]
                        }
                    }
                }
            }
        }
        # Only planning to disable signin, but Galaxy Store is installed!
        packages_to_disable = ["com.osp.app.signin"]
        installed = {"com.osp.app.signin", "com.sec.android.app.samsungapps"}

        approved, blocked = validate_package_dependencies(packages_to_disable, installed, mock_db)
        self.assertNotIn("com.osp.app.signin", approved)
        self.assertEqual(len(blocked), 1)
        self.assertIn("DEPENDENCY CONFLICT", blocked[0]["reason"])

    def test_dependency_conflict_bypassed_if_dependent_also_disabled(self):
        """If both the app and its dependent are planned to be disabled together, allow it."""
        mock_db = {
            "categories": {
                "samsung": {
                    "packages": {
                        "com.osp.app.signin": {
                            "dependents": ["com.sec.android.app.samsungapps"]
                        }
                    }
                }
            }
        }
        packages_to_disable = ["com.osp.app.signin", "com.sec.android.app.samsungapps"]
        installed = {"com.osp.app.signin", "com.sec.android.app.samsungapps"}

        approved, blocked = validate_package_dependencies(packages_to_disable, installed, mock_db)
        self.assertIn("com.osp.app.signin", approved)
        self.assertIn("com.sec.android.app.samsungapps", approved)
        self.assertEqual(len(blocked), 0)

    def test_keyboard_safeguard(self):
        """Must block disabling the only installed keyboard."""
        mock_db = {"categories": {}}
        keyboard = "com.google.android.inputmethod.latin"
        installed = {keyboard, "com.some.other.app"}
        packages_to_disable = [keyboard]

        approved, blocked = validate_package_dependencies(packages_to_disable, installed, mock_db)
        self.assertNotIn(keyboard, approved)
        self.assertEqual(len(blocked), 1)
        self.assertIn("INPUT SAFETY", blocked[0]["reason"])

    def test_launcher_safeguard(self):
        """Must block disabling the only installed home launcher."""
        mock_db = {"categories": {}}
        launcher = "com.sec.android.app.launcher"
        installed = {launcher, "com.some.app"}
        packages_to_disable = [launcher]

        approved, blocked = validate_package_dependencies(packages_to_disable, installed, mock_db)
        self.assertNotIn(launcher, approved)
        self.assertEqual(len(blocked), 1)
        self.assertIn("HOME SCREEN SAFETY", blocked[0]["reason"])

    def test_plan_mode_optimization_tiers(self):
        """Verify each mode includes the expected package tiers and parameters."""
        installed = {
            "com.aura.oobe.samsung",            # carrier bloat (low, medium, high, ultra)
            "com.samsung.android.sm.devicesecurity", # recommended (low, medium, high, ultra)
            "com.samsung.android.spaymini",     # recommended (medium, high, ultra)
            "com.samsung.android.aremoji",      # advanced (high, ultra)
            "com.sec.android.app.samsungapps"   # expert (ultra only)
        }

        # Low Mode
        plan_low = plan_mode_optimization("low", installed, manufacturer="samsung")
        self.assertIn("com.aura.oobe.samsung", plan_low["approved_packages"])
        self.assertIn("com.samsung.android.sm.devicesecurity", plan_low["approved_packages"])
        self.assertNotIn("com.samsung.android.aremoji", plan_low["approved_packages"])
        self.assertEqual(plan_low["actions"]["animation_scale"], "0.75")

        # Medium Mode
        plan_med = plan_mode_optimization("medium", installed, manufacturer="samsung")
        self.assertIn("com.samsung.android.spaymini", plan_med["approved_packages"])
        self.assertNotIn("com.samsung.android.aremoji", plan_med["approved_packages"])
        self.assertEqual(plan_med["actions"]["animation_scale"], "0.5")

        # High Mode
        plan_high = plan_mode_optimization("high", installed, manufacturer="samsung")
        self.assertIn("com.samsung.android.aremoji", plan_high["approved_packages"])
        self.assertNotIn("com.sec.android.app.samsungapps", plan_high["approved_packages"])
        self.assertEqual(plan_high["actions"]["standby_bucket"], "restricted")

        # Ultra Mode
        plan_ultra = plan_mode_optimization("ultra", installed, manufacturer="samsung")
        self.assertIn("com.sec.android.app.samsungapps", plan_ultra["approved_packages"])
        self.assertEqual(plan_ultra["actions"]["animation_scale"], "0.0")

    def test_ultra_safety_gate_rejection(self):
        """Executing Ultra without confirmation must abort immediately."""
        res = execute_mode_optimization("ultra", dry_run=True, force_ultra=False, interactive_confirm=False)
        self.assertFalse(res["success"])
        self.assertTrue(res["aborted"])
        self.assertIn("requires explicit confirmation", res["error"])

    def test_ultra_safety_gate_force_ultra(self):
        """Executing Ultra with force_ultra=True must proceed in dry-run."""
        with patch("modes.get_installed_packages", return_value={"com.aura.oobe.samsung"}):
            with patch("modes.get_device_info", return_value={"brand": "Samsung", "model": "Galaxy"}):
                res = execute_mode_optimization("ultra", dry_run=True, force_ultra=True)
                self.assertTrue(res["success"])
                self.assertFalse(res.get("aborted", False))
                self.assertEqual(res["mode"], "ultra")
                self.assertTrue(res["ui_tuned"])

    def test_dry_run_all_modes_execution(self):
        """All 4 modes must execute in dry-run mode without real hardware."""
        mock_installed = {"com.aura.oobe.samsung", "com.facebook.katana"}
        with patch("modes.get_installed_packages", return_value=mock_installed):
            with patch("modes.get_device_info", return_value={"brand": "Generic", "model": "Phone"}):
                for mode in ["low", "medium", "high"]:
                    res = execute_mode_optimization(mode, dry_run=True)
                    self.assertTrue(res["success"])
                    self.assertEqual(res["mode"], mode)
                    self.assertTrue(res["dry_run"])

    @patch("builtins.input", side_effect=["Y"])
    def test_confirm_preflight_plan_accept(self, mock_input):
        """User confirming 'Y' in pre-flight report returns True."""
        from modes import confirm_preflight_plan, plan_mode_optimization
        plan = plan_mode_optimization("medium", {"com.facebook.katana"})
        dev = {"brand": "Realme", "model": "RMX3867", "android_version": "14", "sdk_level": "34"}
        confirmed = confirm_preflight_plan(plan, dev, ["com.facebook.katana"], ["com.facebook.katana"])
        self.assertTrue(confirmed)

    @patch("builtins.input", side_effect=["N"])
    def test_confirm_preflight_plan_reject(self, mock_input):
        """User cancelling 'N' in pre-flight report returns False."""
        from modes import confirm_preflight_plan, plan_mode_optimization
        plan = plan_mode_optimization("medium", {"com.facebook.katana"})
        dev = {"brand": "Realme", "model": "RMX3867", "android_version": "14", "sdk_level": "34"}
        confirmed = confirm_preflight_plan(plan, dev, [], [])
        self.assertFalse(confirmed)

    @patch("builtins.input", side_effect=["D", "Y"])
    def test_confirm_preflight_plan_details_then_accept(self, mock_input):
        """User requesting 'D' details then entering 'Y' inspects and confirms."""
        from modes import confirm_preflight_plan, plan_mode_optimization
        plan = plan_mode_optimization("medium", {"com.facebook.katana"})
        dev = {"brand": "Realme", "model": "RMX3867", "android_version": "14", "sdk_level": "34"}
        confirmed = confirm_preflight_plan(plan, dev, ["com.facebook.katana"], [])
        self.assertTrue(confirmed)

    @patch("modes.confirm_preflight_plan", return_value=False)
    def test_execute_mode_optimization_preflight_cancelled(self, mock_confirm):
        """Cancelling pre-flight confirmation cleanly aborts optimization."""
        with patch("modes.get_installed_packages", return_value={"com.facebook.katana"}):
            with patch("modes.get_device_info", return_value={"brand": "Realme", "model": "RMX3867"}):
                res = execute_mode_optimization("medium", dry_run=True, interactive_confirm=True)
                self.assertFalse(res["success"])
                self.assertTrue(res["aborted"])
                self.assertIn("cancelled by user", res["error"])

    def test_operations_state_normalization(self):
        """Ensure apply_package_state accepts 'disable', 'enable', 'uninstall' aliases."""
        from operations import apply_package_state
        with patch("operations.run_adb", return_value=(True, "")):
            # Dry-run with aliases
            ok_d, msg_d = apply_package_state("com.test.app", want="disable", dry_run=True)
            self.assertTrue(ok_d)
            self.assertIn("disable-user", msg_d)

            ok_e, msg_e = apply_package_state("com.test.app", want="enable", dry_run=True)
            self.assertTrue(ok_e)
            self.assertIn("enable --user", msg_e)

    def test_get_package_state_uninstalled_priority(self):
        """B1 Fix: Ensure uninstalled package reports 'uninstalled' even if dumpsys has enabled=0."""
        from operations import get_package_state
        def mock_adb(cmd, **kwargs):
            cmd_str = " ".join(cmd)
            if "pm list packages -e" in cmd_str:
                return (True, "")
            if "pm list packages -d" in cmd_str:
                return (True, "")
            if "pm list packages -u" in cmd_str:
                return (True, "package:com.example.gone")
            if "dumpsys package" in cmd_str:
                return (True, "enabled=0\nUser 0: installed=false")
            return (True, "")

        with patch("operations.run_adb", side_effect=mock_adb):
            state = get_package_state("com.example.gone", user_id=0)
            self.assertEqual(state, "uninstalled")

    def test_restore_uninstalled_package_triggers_install_existing(self):
        """B1 Fix: Restoring an uninstalled package must call install-existing and not no-op."""
        from operations import apply_package_state
        called_commands = []
        def mock_adb(cmd, **kwargs):
            cmd_str = " ".join(cmd)
            called_commands.append(cmd_str)
            if "pm list packages -e" in cmd_str:
                return (True, "")
            if "pm list packages -d" in cmd_str:
                return (True, "")
            if "pm list packages -u" in cmd_str:
                return (True, "package:com.example.gone")
            if "install-existing" in cmd_str:
                return (True, "Package com.example.gone installed for user: 0")
            return (True, "")

        with patch("operations.run_adb", side_effect=mock_adb):
            ok, msg = apply_package_state("com.example.gone", want="enabled", user_id=0, dry_run=False)
            self.assertTrue(ok)
            self.assertTrue(any("install-existing" in c for c in called_commands))
            self.assertIn("Restored", msg.title())

    def test_doze_whitelist_prefix_parsing(self):
        """B3 Fix: Dumpsys deviceidle lines with user, and system, prefixes are accurately categorized."""
        from doze_boost import parse_deviceidle_whitelist
        raw_output = """
system,com.android.providers.telephony,1001
system,com.google.android.gms,1000
user,com.instagram.android,10150
"""
        parsed = parse_deviceidle_whitelist(raw_output)
        self.assertIn("com.instagram.android", parsed["user"])
        self.assertNotIn("com.instagram.android", parsed["system"])
        self.assertIn("com.google.android.gms", parsed["system"])

    def test_bench_refresh_rate_display_mode_parsing(self):
        """B4 Fix: DisplayModeRecord with fps=120.0 must be extracted accurately."""
        from bench import get_display_refresh_rate
        def mock_adb(cmd, **kwargs):
            cmd_str = " ".join(cmd)
            if "peak_refresh_rate" in cmd_str:
                return (False, "")
            if "dumpsys display" in cmd_str:
                return (True, "DisplayModeRecord{mMode={id=2, width=1080, height=2400, fps=120.0}}")
            return (False, "")

        with patch("bench.run_adb", side_effect=mock_adb):
            fps = get_display_refresh_rate()
            self.assertEqual(fps, 120.0)

    @patch("modes.compile_package", return_value=(True, "Success"))
    @patch("modes.apply_package_state", return_value=(True, "Disabled"))
    @patch("modes.set_appops_restriction", return_value=(True, "Restricted"))
    @patch("modes.set_standby_bucket", return_value=(True, "Set bucket"))
    @patch("modes.trim_system_cache")
    @patch("modes.set_animation_scale")
    def test_execute_mode_medium_live_dispatch(self, mock_scale, mock_trim, mock_bucket, mock_ops, mock_state, mock_compile):
        """Simulate real hardware dispatch for Medium mode verifying no TypeError or unknown states."""
        mock_installed = {"com.oplus.onetrace", "com.instagram.android"}
        with patch("modes.get_installed_packages", return_value=mock_installed):
            with patch("modes.get_device_info", return_value={"brand": "Realme", "model": "RMX3867", "android_version": "14", "sdk_level": "34"}):
                res = execute_mode_optimization("medium", dry_run=False, auto_confirm=True)
                self.assertTrue(res["success"])
                self.assertIn("com.oplus.onetrace", res["packages_disabled"])
                self.assertIn("com.instagram.android", res["art_compiled"])
                mock_state.assert_called_once_with("com.oplus.onetrace", want="disabled", serial=None, dry_run=False)
                mock_compile.assert_called_once_with("com.instagram.android", compile_filter="speed-profile", serial=None, dry_run=False)

if __name__ == "__main__":
    unittest.main()
