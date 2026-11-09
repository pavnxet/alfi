"""
scripts/ui - ALFi's terminal layer (standard library only).

    from ui import out, ui

    ui = UI()                 # resolves caps + theme once
    print(ui.box(["hello"]))  # list of lines, exactly ui.width columns wide

Design rules, enforced by tests/test_ui.py:

1. Widgets are pure: data + width + theme in, strings out.
2. Every pad/truncate goes through widgets.display_width(), so emoji and ANSI
   never break a border again.
3. When stdout is not a TTY: no colour, no cursor movement, ASCII borders.
4. Nothing here imports a third-party package, and nothing calls `adb`.
"""

from __future__ import annotations

import sys

from . import keys, prompts, term, theme, widgets
from .theme import Theme, make_theme
from .widgets import (
    bar,
    badge,
    box,
    display_width,
    glyphs,
    kv_rows,
    pad,
    progress_bar,
    rule,
    status_line,
    strip_ansi,
    table,
    truncate,
)

__all__ = [
    "UI", "ui", "out",
    "term", "theme", "widgets", "keys", "prompts",
    "Theme", "make_theme",
    "bar", "badge", "box", "display_width", "glyphs", "kv_rows", "pad",
    "progress_bar", "rule", "status_line", "strip_ansi", "table", "truncate",
]


def out(text="", stream=None):
    """The single write path. Non-TTY output is written one plain line at a time."""
    stream = stream or sys.stdout
    try:
        stream.write(str(text) + "\n")
        stream.flush()
    except Exception:
        pass


class UI(object):
    """Capabilities + theme + layout, resolved once per process."""

    def __init__(self, caps=None, theme_obj=None):
        self.caps = caps or term.caps()
        self.theme = theme_obj or make_theme(self.caps)
        self.glyph = glyphs(self.caps.unicode)
        self.width = self.caps.layout_width

    # -- rendering ---------------------------------------------------------
    def box(self, lines, width=None, title=None):
        return box(lines, width or self.width, theme=self.theme,
                   glyph=self.glyph, title=title)

    def status(self, items, width=None):
        return status_line(items, width or self.width, theme=self.theme,
                           glyph=self.glyph)

    def kv(self, pairs, label_width=None):
        return kv_rows(pairs, label_width=label_width, theme=self.theme)

    def badge(self, tier):
        return badge(tier, theme=self.theme, glyph=self.glyph)

    def bar(self, value, maximum, width=20, role="ok"):
        return bar(value, maximum, width, theme=self.theme, role=role,
                   glyph=self.glyph)

    def progress(self, done, total, width=None, label=""):
        return progress_bar(done, total, width or self.width, theme=self.theme,
                            label=label)

    def rule(self, width=None):
        return rule(width or self.width, theme=self.theme, char=self.glyph["h"])

    def table(self, headers, rows, widths):
        return table(headers, rows, widths, theme=self.theme)

    # -- output ------------------------------------------------------------
    def print(self, *lines):
        """Print strings or lists of strings through the single write path."""
        for line in lines:
            if isinstance(line, (list, tuple)):
                for sub in line:
                    out(sub)
            else:
                out(line)

    def clear(self):
        """Clear the screen only when it is safe to do so."""
        if not self.caps.is_tty or self.caps.no_color:
            return
        try:
            sys.stdout.write("\033[H\033[2J\033[3J")
            sys.stdout.flush()
        except Exception:
            pass


_ui = None


def ui():
    """Process-wide UI instance."""
    global _ui
    if _ui is None:
        _ui = UI()
    return _ui


def reset_ui():
    """Rebuild the UI (tests change env vars and need a fresh detection)."""
    global _ui
    term.reset_caps()
    _ui = None
