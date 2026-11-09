"""
scripts/ui/keys.py - Single-keypress reading, stdlib only.

POSIX uses termios/tty raw mode, Windows uses msvcrt. When neither is available
(piped stdin, dumb console, CI) every entry point returns None and the caller
falls back to line-based input, so the UI never hangs waiting for a key that
cannot arrive.
"""

from __future__ import annotations

import os
import sys

KEY_UP = "up"
KEY_DOWN = "down"
KEY_LEFT = "left"
KEY_RIGHT = "right"
KEY_ENTER = "enter"
KEY_ESC = "esc"
KEY_BACKSPACE = "backspace"

_ARROWS = {
    "\x1b[A": KEY_UP,
    "\x1b[B": KEY_DOWN,
    "\x1b[C": KEY_RIGHT,
    "\x1b[D": KEY_LEFT,
    "\x1bOA": KEY_UP,
    "\x1bOB": KEY_DOWN,
    "\x1bOC": KEY_RIGHT,
    "\x1bOD": KEY_LEFT,
}


def raw_available():
    """True when a single keypress can be read without pressing Enter."""
    try:
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            return False
    except Exception:
        return False
    if os.name == "nt":
        try:
            import msvcrt  # noqa: F401
        except Exception:
            return False
        return True
    try:
        import termios  # noqa: F401
        import tty  # noqa: F401
    except Exception:
        return False
    return True


def read_key(timeout=None):
    """Read one keypress and normalise it. Returns None when unavailable."""
    if not raw_available():
        return None
    if os.name == "nt":
        return _read_key_windows()
    return _read_key_posix(timeout)


def _read_key_posix(timeout=None):
    import select

    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        if timeout is not None:
            ready, _, _ = select.select([fd], [], [], timeout)
            if not ready:
                return None
        first = os.read(fd, 1).decode("utf-8", "replace")
        if first != "\x1b":
            return _normalise(first)
        # Possible escape sequence: read what is immediately available.
        seq = first
        for _ in range(2):
            ready, _, _ = select.select([fd], [], [], 0.02)
            if not ready:
                break
            seq += os.read(fd, 1).decode("utf-8", "replace")
        return _ARROWS.get(seq, KEY_ESC)
    except Exception:
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _read_key_windows():
    try:
        import msvcrt

        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            code = msvcrt.getwch()
            return {"H": KEY_UP, "P": KEY_DOWN, "K": KEY_LEFT, "M": KEY_RIGHT}.get(code)
        return _normalise(ch)
    except Exception:
        return None


def _normalise(ch):
    if ch in ("\r", "\n"):
        return KEY_ENTER
    if ch in ("\x7f", "\x08"):
        return KEY_BACKSPACE
    if ch == "\x1b":
        return KEY_ESC
    if ch == "\x03":
        raise KeyboardInterrupt()
    if ch == "\x04":
        return KEY_ESC  # Ctrl-D behaves like "leave this screen"
    return ch
