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

    @patch("builtins.input", side_effect=["1"])
    @patch("wizard.run_wizard_action", return_value=(True, "Low mode applied"))
    def test_prompt_mode_selection_low(self, mock_run, mock_input):
        """Selecting [1] routes to Low mode without safety gate."""
        ok, out = prompt_mode_selection(dry_run=True)
        self.assertTrue(ok)
        mock_run.assert_called_once_with("modes", dry_run=True, extra_args=["--mode", "low"])

    @patch("builtins.input", side_effect=["4", "NOPE"])
    def test_prompt_mode_selection_ultra_aborted(self, mock_input):
        """Selecting [4] Ultra and failing to type 'I UNDERSTAND' aborts execution."""
        ok, out = prompt_mode_selection(dry_run=True)
        self.assertFalse(ok)
        self.assertIn("Safety Gate", out)

    @patch("builtins.input", side_effect=["4", "I UNDERSTAND"])
    @patch("wizard.run_wizard_action", return_value=(True, "Ultra mode applied"))
    def test_prompt_mode_selection_ultra_confirmed(self, mock_run, mock_input):
        """Selecting [4] Ultra and typing 'I UNDERSTAND' proceeds with --force-ultra."""
        ok, out = prompt_mode_selection(dry_run=True)
        self.assertTrue(ok)
        mock_run.assert_called_once_with(
            "modes",
            dry_run=True,
            extra_args=["--mode", "ultra", "--force-ultra"]
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

if __name__ == "__main__":
    unittest.main()
