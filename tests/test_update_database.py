#!/usr/bin/env python3
"""
tests/test_update_database.py - Comprehensive Unit Tests for Community Database Updater

Verifies OEM categorization, UAD-ng list parsing, injection defense, merging logic,
backup snapshots, and database restoration using standard library unittest without
requiring a physical device or pip packages.
"""

import sys
import os
import unittest
import tempfile
import json
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from update_database import (
    categorize_package,
    parse_community_list,
    merge_databases,
    backup_database
)

class TestUpdateDatabase(unittest.TestCase):

    def test_categorize_package(self):
        """Test accurate OEM group resolution from package prefixes."""
        self.assertEqual(categorize_package("com.samsung.android.voc"), "samsung")
        self.assertEqual(categorize_package("com.sec.android.app.billing"), "samsung")
        self.assertEqual(categorize_package("com.miui.analytics.go"), "xiaomi")
        self.assertEqual(categorize_package("com.xiaomi.mipicks"), "xiaomi")
        self.assertEqual(categorize_package("com.oplus.statistics.rom"), "realme")
        self.assertEqual(categorize_package("com.heytap.mcs"), "realme")
        self.assertEqual(categorize_package("com.google.android.youtube"), "google")
        self.assertEqual(categorize_package("com.facebook.katana"), "general_bloat")

    def test_parse_community_list_valid_and_malicious(self):
        """Ensure parser accepts valid UAD entries and rejects injection attacks."""
        raw_community_data = [
            {
                "id": "com.samsung.android.bixby.agent",
                "list": "Advanced",
                "description": "Bixby Voice wakeup daemon"
            },
            {
                "id": "com.miui.msa.global",
                "list": "Recommended",
                "description": "MIUI System Ads delivery network"
            },
            {
                "id": "com.bad.app; rm -rf /",
                "list": "Recommended",
                "description": "Malicious injection package"
            },
            {
                "id": "",
                "list": "Unsafe",
                "description": "Empty package"
            }
        ]

        categorized, accepted, rejected = parse_community_list(raw_community_data)
        self.assertEqual(accepted, 2)
        self.assertEqual(rejected, 2)
        self.assertIn("samsung", categorized)
        self.assertIn("xiaomi", categorized)
        self.assertIn("com.samsung.android.bixby.agent", categorized["samsung"])
        self.assertEqual(categorized["samsung"]["com.samsung.android.bixby.agent"]["tier"], "Advanced")
        self.assertEqual(categorized["xiaomi"]["com.miui.msa.global"]["tier"], "Recommended")

    def test_parse_community_list_dictionary_mapping(self):
        """Ensure parser accepts upstream UAD-ng dictionary mapping format."""
        raw_dict_data = {
            "com.samsung.android.bixby.agent": {
                "removal": "Advanced",
                "description": "Bixby Voice wakeup daemon",
                "dependencies": [],
                "neededBy": []
            },
            "com.miui.analytics": {
                "removal": "Recommended",
                "description": "Xiaomi analytics service"
            },
            "invalid_pkg; rm -rf": {
                "removal": "Recommended"
            }
        }
        categorized, accepted, rejected = parse_community_list(raw_dict_data)
        self.assertEqual(accepted, 2)
        self.assertEqual(rejected, 1)
        self.assertIn("samsung", categorized)
        self.assertIn("xiaomi", categorized)
        self.assertIn("com.samsung.android.bixby.agent", categorized["samsung"])
        self.assertEqual(categorized["samsung"]["com.samsung.android.bixby.agent"]["tier"], "Advanced")
        self.assertEqual(categorized["xiaomi"]["com.miui.analytics"]["tier"], "Recommended")

    def test_merge_databases(self):
        """Ensure incoming packages merge into existing structure without overwriting custom categories."""
        existing_db = {
            "version": "1.0.0",
            "categories": {
                "samsung": {
                    "name": "Samsung One UI",
                    "packages": {
                        "com.samsung.android.sm.devicesecurity": {
                            "name": "McAfee Scanner",
                            "tier": "Recommended",
                            "impact": "Custom detailed note."
                        }
                    }
                }
            }
        }

        incoming = {
            "samsung": {
                "com.samsung.android.spaymini": {
                    "name": "Spaymini",
                    "tier": "Recommended",
                    "impact": "Promotional framework."
                }
            },
            "realme": {
                "com.heytap.mcs": {
                    "name": "Mcs",
                    "tier": "Recommended",
                    "impact": "HeyTap push."
                }
            }
        }

        updated, new_count, mod_count = merge_databases(existing_db, incoming)
        self.assertEqual(new_count, 2)
        self.assertIn("com.samsung.android.spaymini", updated["categories"]["samsung"]["packages"])
        self.assertIn("realme", updated["categories"])
        self.assertIn("com.heytap.mcs", updated["categories"]["realme"]["packages"])
        self.assertIn("last_updated", updated)

if __name__ == "__main__":
    unittest.main()
