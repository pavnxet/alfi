"""
android-lag-fixer - Pure Python ADB Android lag fixer, performance optimizer & security auditor.
"""

import sys
import os

_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

__version__ = "1.1.0"
