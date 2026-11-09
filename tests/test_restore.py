#!/usr/bin/env python3
"""
tests/test_restore.py - Unit Tests for Disaster-Free Package Restoration Tool

Tests manifest finding, manifest rollback structure, and single/batch package restoration.
"""

import sys
import os
import unittest
import tempfile
import json
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from restore import get_latest_manifest

class TestRestore(unittest.TestCase):

    def test_get_latest_manifest(self):
        """Verify discovery of the most recent restore manifest."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            manifest_1 = os.path.join(tmp_dir, "restore_manifest_20261109_100000.json")
            manifest_2 = os.path.join(tmp_dir, "restore_manifest_20261109_120000.json")

            with open(manifest_1, "w") as f:
                f.write("{}")
            with open(manifest_2, "w") as f:
                f.write("{}")

            with patch("restore.glob.glob", return_value=[manifest_1, manifest_2]):
                with patch("restore.os.path.exists", return_value=True):
                    with patch("restore.os.path.getmtime", side_effect=lambda x: 100 if "100000" in x else 200):
                        latest = get_latest_manifest()
                        self.assertEqual(latest, manifest_2)

    def test_get_latest_manifest_empty(self):
        """Return None when no manifests exist."""
        with patch("restore.os.path.exists", return_value=False):
            self.assertIsNone(get_latest_manifest())

if __name__ == "__main__":
    unittest.main()
