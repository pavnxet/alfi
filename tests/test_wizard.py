#!/usr/bin/env python3
"""
tests/test_wizard.py - Comprehensive Unit Tests for Interactive Terminal Wizard

Verifies action map integrity, script existence on disk, menu structure, scrcpy detection,
interactive mode selection prompts, Ultra safety gates, and non-interactive CLI execution simulation.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from wizard import (
    ACTIONS_MAP,
    MENU_ORDER,
    run_wizard_action,
    find_scrcpy_binary,
    launch_scrcpy,
    prompt_mode_selection,
    prompt_device_selection,
    print_device_card,
    print_menu,
    SCRIPTS_DIR
)

class TestWizard(unittest.TestCase):

    def test_actions_map_script_existence(self):
        """Ensure every action mapped in the wizard corresponds to an existing script on disk."""
        for key, entry in ACTIONS_MAP.items():
            script_path = os.path.join(SCRIPTS_DIR, entry["script"])
            self.assertTrue(
                os.path.exists(script_path),
                f"Action '{key}' references missing script: {entry['script']}"
            )
            self.assertTrue(entry["title"].strip() != "")

    def test_menu_order_coverage(self):
        """Ensure all menu items correspond to registered actions in ACTIONS_MAP."""
        for num, key in MENU_ORDER:
            self.assertIn(key, ACTIONS_MAP, f"Menu item '{num}' ({key}) missing from ACTIONS_MAP")

    def test_run_unknown_action(self):
        """Reject unmapped action keys cleanly."""
        ok, msg = run_wizard_action("teleport_device")
        self.assertFalse(ok)
        self.assertIn("Unknown action", msg)

    @patch("wizard.subprocess.run")
    def test_run_wizard_action_dry_run(self, mock_subproc):
        """Verify command construction and dry-run flag propagation."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Dry-run completed successfully"
        mock_subproc.return_value = mock_proc

        ok, out = run_wizard_action("modes", dry_run=True, extra_args=["--mode", "low"])
        self.assertTrue(ok)
        self.assertEqual(out, "Dry-run completed successfully")

        args, kwargs = mock_subproc.call_args
        cmd = args[0]
        self.assertIn("modes.py", cmd[1])
        self.assertIn("--dry-run", cmd)
        self.assertIn("--mode", cmd)
        self.assertIn("low", cmd)

    @patch("wizard.shutil.which", return_value="/usr/bin/scrcpy")
    def test_find_scrcpy_on_path(self, mock_which):
        """Detect scrcpy when installed on system PATH."""
        found = find_scrcpy_binary()
        self.assertEqual(found, "/usr/bin/scrcpy")

    @patch("wizard.subprocess.Popen")
    @patch("wizard.find_scrcpy_binary", return_value="E:\\scrcpy.exe")
    def test_launch_scrcpy_success(self, mock_find, mock_popen):
        """Verify scrcpy launch command arguments."""
        ok, msg = launch_scrcpy()
        self.assertTrue(ok)
        self.assertIn("Launched real-time screen mirror", msg)
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        self.assertEqual(args[0], "E:\\scrcpy.exe")
        self.assertIn("--stay-awake", args)

    @patch("builtins.input", side_effect=["1", "Y"])
    @patch("wizard.run_wizard_action", return_value=(True, "Low mode applied"))
    def test_prompt_mode_selection_low(self, mock_run, mock_input):
        """Selecting [1] and confirming 'Y' in pre-flight report routes to Low mode."""
        ok, out = prompt_mode_selection(dry_run=True)
        self.assertTrue(ok)
        mock_run.assert_called_once_with("modes", dry_run=True, extra_args=["--mode", "low", "--yes"], serial=None)

    @patch("builtins.input", side_effect=["2", "N"])
    def test_prompt_mode_selection_cancelled(self, mock_input):
        """Selecting [2] and cancelling 'N' in pre-flight report aborts with zero changes."""
        ok, out = prompt_mode_selection(dry_run=True)
        self.assertFalse(ok)
        self.assertIn("cancelled by user", out.lower())

    @patch("builtins.input", side_effect=["2", "D", "Y"])
    @patch("wizard.run_wizard_action", return_value=(True, "Medium mode applied"))
    def test_prompt_mode_selection_details_then_confirmed(self, mock_run, mock_input):
        """Selecting [2], inspecting details 'D', then confirming 'Y' proceeds with optimization."""
        ok, out = prompt_mode_selection(dry_run=True)
        self.assertTrue(ok)
        mock_run.assert_called_once_with("modes", dry_run=True, extra_args=["--mode", "medium", "--yes"], serial=None)

    @patch("builtins.input", side_effect=["4", "Y", "NOPE"])
    def test_prompt_mode_selection_ultra_aborted(self, mock_input):
        """Selecting [4] Ultra and failing to type 'I UNDERSTAND' aborts execution."""
        ok, out = prompt_mode_selection(dry_run=True)
        self.assertFalse(ok)
        self.assertIn("Safety Gate", out)

    @patch("builtins.input", side_effect=["4", "Y", "I UNDERSTAND"])
    @patch("wizard.run_wizard_action", return_value=(True, "Ultra mode applied"))
    def test_prompt_mode_selection_ultra_confirmed(self, mock_run, mock_input):
        """Selecting [4] Ultra, confirming pre-flight 'Y', and typing 'I UNDERSTAND' proceeds."""
        ok, out = prompt_mode_selection(dry_run=True)
        self.assertTrue(ok)
        mock_run.assert_called_once_with(
            "modes",
            dry_run=True,
            extra_args=["--mode", "ultra", "--yes", "--force-ultra"],
            serial=None
        )

    @patch("wizard.subprocess.run")
    def test_run_wizard_action_failure_card(self, mock_subproc):
        """Ensure non-zero exit codes are shielded inside formatted status cards."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "Simulated internal script failure"
        mock_subproc.return_value = mock_proc

        ok, out = run_wizard_action("bench")
        self.assertFalse(ok)
        self.assertIn("ACTION NOTIFICATION (Exit Code 1)", out)
        self.assertIn("Simulated internal script failure", out)

    @patch("wizard.subprocess.run", side_effect=OSError("Process spawn failure"))
    def test_run_wizard_action_exception_handling(self, mock_subproc):
        """Ensure OS-level process exceptions are caught cleanly."""
        ok, out = run_wizard_action("modes")
        self.assertFalse(ok)
        self.assertIn("EXECUTION FAILED", out)

    @patch("wizard.get_device_info", return_value={"brand": "Google", "model": "Pixel 7", "android_version": "14", "sdk_level": "34"})
    @patch("wizard.get_connected_devices", return_value=[
        {"serial": "USB_DEV_1", "status": "device"},
        {"serial": "192.168.1.55:5555", "status": "device"}
    ])
    @patch("builtins.input", side_effect=["2"])
    def test_prompt_device_selection_switch(self, mock_input, mock_get_devs, mock_info):
        """Test switching active device from phone 1 to phone 2."""
        chosen_serial, info = prompt_device_selection(current_serial="USB_DEV_1")
        self.assertEqual(chosen_serial, "192.168.1.55:5555")
        self.assertEqual(os.environ.get("ANDROID_SERIAL"), "192.168.1.55:5555")
        self.assertEqual(info.get("model"), "Pixel 7")

    @patch("wizard.get_connected_devices", return_value=[{"serial": "DEV_1", "status": "device"}])
    @patch("builtins.input", side_effect=["0"])
    def test_prompt_device_selection_return_zero(self, mock_input, mock_get_devs):
        """Entering '0' exits selector and preserves current serial."""
        chosen_serial, _ = prompt_device_selection(current_serial="DEV_1")
        self.assertEqual(chosen_serial, "DEV_1")

    @patch("wizard.get_connected_devices", return_value=[
        {"serial": "UNAUTH_DEV", "status": "unauthorized"}
    ])
    @patch("builtins.input", side_effect=["1", "", "0"])
    def test_prompt_device_selection_unauthorized_blocked(self, mock_input, mock_get_devs):
        """Selecting an unauthorized device warns and blocks target switch."""
        chosen_serial, _ = prompt_device_selection(current_serial=None)
        self.assertIsNone(chosen_serial)

    def test_print_device_card_render_modes(self):
        """Verify device card renders correctly across different device states."""
        # Active device
        info = {"brand": "Samsung", "model": "S23", "android_version": "14", "sdk_level": "34", "security_patch": "2024-05-01"}
        print_device_card(info, total_devices=1, active_serial="R5CT123456")
        
        # Multiple devices
        print_device_card(info, total_devices=2, active_serial="R5CT123456")
        
        # Unauthorized devices only
        print_device_card(None, total_devices=1, active_serial=None)
        
        # Zero devices
        print_device_card(None, total_devices=0, active_serial=None)

    def test_print_menu_render(self):
        """Verify menu renders correctly with device switch options."""
        print_menu(total_devices=1)
        print_menu(total_devices=3)

if __name__ == "__main__":
    unittest.main()
