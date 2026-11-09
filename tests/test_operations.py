#!/usr/bin/env python3
"""
tests/test_operations.py - Unit tests for package state validation & Android 17 resolution
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from operations import validate_package_name, apply_package_state

def test_validate_package_name_valid():
    assert validate_package_name("com.android.chrome") is True
    assert validate_package_name("com.facebook.katana") is True
    assert validate_package_name("org.videolan.vlc") is True
    assert validate_package_name("com.example.app_one") is True

def test_validate_package_name_invalid_injection():
    assert validate_package_name("com.example; rm -rf /") is False
    assert validate_package_name("com.app$(whoami)") is False
    assert validate_package_name("com.app | cat /etc/passwd") is False
    assert validate_package_name("") is False
    assert validate_package_name("invalid_single_word") is False

def test_dry_run_state_application():
    ok, msg = apply_package_state("com.android.chrome", want="disabled", dry_run=True)
    assert ok is True
    assert "[DRY-RUN]" in msg
    assert "pm disable-user --user 0 com.android.chrome" in msg

def test_android_17_uninstall_fallback():
    # SDK 37 (Android 17) must fall back from uninstalled to disabled
    ok, msg = apply_package_state("com.android.chrome", want="uninstalled", sdk_level=37, dry_run=True)
    assert ok is True
    assert "pm disable-user" in msg
