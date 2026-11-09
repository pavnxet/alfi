#!/usr/bin/env python3
"""
tests/test_wizard.py - Comprehensive Unit Tests for Interactive Terminal Wizard

Verifies action map integrity, script existence on disk, menu structure, and non-interactive
CLI execution simulation using standard unittest and unittest.mock.
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

        ok, out = run_wizard_action("debloat", dry_run=True)
        self.assertTrue(ok)
        self.assertEqual(out, "Dry-run completed successfully")

        # Verify command arguments passed to subprocess
        args, kwargs = mock_subproc.call_args
        cmd = args[0]
        self.assertIn("optimize.py", cmd[1])
        self.assertIn("--dry-run", cmd)

if __name__ == "__main__":
    unittest.main()
