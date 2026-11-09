"""
scripts/ui/term.py - Terminal capability detection (stdlib only).

Everything the UI needs to know about *where* it is drawing lives here, so that
no other module has to guess: TTY-ness, colour depth, unicode support, size,
and whether Windows virtual-terminal processing has been enabled.
"""

from __future__ import annotations

import os
import shutil
import sys

# Layout bounds. Boxes never exceed LAYOUT_MAX so a 4K terminal does not produce
# a 300-column card, and never go below LAYOUT_MIN so borders stay readable.
LAYOUT_MIN = 40
LAYOUT_MAX = 100
LAYOUT_DEFAULT = 74


class TermCaps(object):
    """Resolved terminal capabilities for this process."""

    def __init__(self, stream=None, stdin=None):
        stream = stream if stream is not None else sys.stdout
        stdin = stdin if stdin is not None else sys.stdin

        self.is_tty = self._isatty(stream)
        self.stdin_is_tty = self._isatty(stdin)
        self.no_color = self._no_color()
        self.unicode = self._unicode(stream)
        self.color_depth = self._color_depth()
        self.width, self.height = self._size()
        self.vt_enabled = enable_windows_vt()

    # -- detection ---------------------------------------------------------
    @staticmethod
    def _isatty(stream):
        try:
            return bool(stream.isatty())
        except Exception:
            return False

    def _no_color(self):
        if "NO_COLOR" in os.environ:
            return True
        if os.environ.get("ALFI_NO_COLOR"):
            return True
        if os.environ.get("TERM", "").lower() == "dumb":
            return True
        return not self.is_tty

    def _unicode(self, stream):
        if os.environ.get("ALFI_ASCII"):
            return False
        if not self.is_tty:
            # Piped output goes to logs and bug reports: plain ASCII travels best.
            return False
        enc = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
        return "utf" in enc

    def _color_depth(self):
        if self.no_color:
            return "none"
        colorterm = os.environ.get("COLORTERM", "").lower()
        if colorterm in ("truecolor", "24bit"):
            return "truecolor"
        term = os.environ.get("TERM", "").lower()
        if "256" in term:
            return "256"
        if os.name == "nt" and not os.environ.get("TERM"):
            # Windows Terminal advertises itself via WT_SESSION
            return "truecolor" if os.environ.get("WT_SESSION") else "16"
        return "16"

    def _size(self):
        try:
            size = shutil.get_terminal_size((80, 24))
            return max(20, size.columns), max(10, size.lines)
        except Exception:
            return 80, 24

    # -- derived -----------------------------------------------------------
    @property
    def layout_width(self):
        """Width for cards and boxes: the terminal width, clamped to sane bounds."""
        return max(LAYOUT_MIN, min(LAYOUT_MAX, self.width))

    @property
    def compact(self):
        """True when the terminal is too narrow for the two-column layouts."""
        return self.width < 60

    def describe(self):
        return "tty=%s color=%s unicode=%s %dx%d" % (
            self.is_tty, self.color_depth, self.unicode, self.width, self.height)


def enable_windows_vt():
    """Turn on ANSI escape processing in Windows consoles. No-op elsewhere."""
    if os.name != "nt":
        return False
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        return bool(kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING))
    except Exception:
        return False


_caps = None


def caps():
    """Process-wide capabilities (cached; tests may call reset_caps())."""
    global _caps
    if _caps is None:
        _caps = TermCaps()
    return _caps


def reset_caps():
    """Drop the cache so the next caps() call re-detects (used by tests)."""
    global _caps
    _caps = None
