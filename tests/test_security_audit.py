#!/usr/bin/env python3
"""
tests/test_security_audit.py - Unit Tests for Remote Malware & Privacy Auditor

Tests 3rd-party package parsing, Accessibility service detection, and high-risk permission audits.
"""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from security_audit import (
    get_installed_third_party_packages,
    get_enabled_accessibility_services,
    DANGEROUS_PERMS
)

class TestSecurityAudit(unittest.TestCase):

    @patch("security_audit.run_adb")
    def test_get_installed_third_party_packages(self, mock_adb):
        """Test parsing pm list packages -3 -i output."""
        sample_output = (
            "package:com.whatsapp installer=com.android.vending\n"
            "package:com.spotify.music installer=com.android.vending\n"
            "package:com.unknown.sideload installer=null\n"
        )
        mock_adb.return_value = (True, sample_output)

        pkgs = get_installed_third_party_packages()
        self.assertEqual(len(pkgs), 3)
        self.assertEqual(pkgs["com.whatsapp"], "com.android.vending")
        self.assertEqual(pkgs["com.unknown.sideload"], "null")

    @patch("security_audit.run_adb")
    def test_get_enabled_accessibility_services(self, mock_adb):
        """Detect apps registered in secure settings accessibility services."""
        mock_adb.return_value = (True, "com.suspicious.app/com.suspicious.app.AccService:com.google.android.marvin.talkback/com.google.android.marvin.talkback.TalkBackService")

        services = get_enabled_accessibility_services()
        self.assertEqual(len(services), 2)
        self.assertIn("com.suspicious.app", services)
        self.assertIn("com.google.android.marvin.talkback", services)

    def test_dangerous_permissions_list(self):
        """Ensure critical high-risk Android permissions are tracked."""
        self.assertIn("android.permission.BIND_ACCESSIBILITY_SERVICE", DANGEROUS_PERMS)
        self.assertIn("android.permission.SYSTEM_ALERT_WINDOW", DANGEROUS_PERMS)
        self.assertIn("android.permission.RECEIVE_SMS", DANGEROUS_PERMS)

if __name__ == "__main__":
    unittest.main()
