"""
scripts/ui/theme.py - One semantic palette, resolved per terminal.

Callers ask for a role ("ok", "danger", "muted") and never for a colour, so a
theme change or a no-colour terminal is a single switch. Every colour is also
paired with a glyph by the widgets, so nothing depends on colour alone.
"""

from __future__ import annotations

RESET = "\033[0m"

# 16-colour fallbacks for terminals that do not do 256/truecolor.
_BASIC = {
    "ok": "32",
    "warn": "33",
    "danger": "31",
    "info": "36",
    "accent": "35",
    "muted": "90",
    "title": "1;37",
    "bold": "1",
    "dim": "2",
}

# 256-colour approximations of the ALFi neon identity.
_X256 = {
    "ok": "38;5;42",
    "warn": "38;5;226",
    "danger": "38;5;203",
    "info": "38;5;51",
    "accent": "38;5;213",
    "muted": "38;5;245",
    "title": "1;38;5;231",
    "bold": "1",
    "dim": "2",
}

# Truecolor palettes. `neon` is the original identity; the others are one-line
# alternatives selectable with ALFI_THEME or `alfi config set theme amber`.
PRESETS = {
    "neon": {
        "ok": "38;2;0;230;118",
        "warn": "38;2;255;235;59",
        "danger": "38;2;255;82;82",
        "info": "38;2;0;229;255",
        "accent": "38;2;255;152;0",
        "muted": "38;2;120;144;156",
        "title": "1;38;2;255;255;255",
    },
    "amber": {
        "ok": "38;2;120;220;120",
        "warn": "38;2;255;190;60",
        "danger": "38;2;255;110;70",
        "info": "38;2;255;210;140",
        "accent": "38;2;255;160;40",
        "muted": "38;2;150;130;100",
        "title": "1;38;2;255;240;210",
    },
    "mono": {
        "ok": "38;2;235;235;235",
        "warn": "38;2;200;200;200",
        "danger": "38;2;255;255;255",
        "info": "38;2;190;190;190",
        "accent": "38;2;220;220;220",
        "muted": "38;2;120;120;120",
        "title": "1;38;2;255;255;255",
    },
}

# Truecolor, matching the original hard-coded literals.
_TRUECOLOR = {
    "ok": "38;2;0;230;118",
    "warn": "38;2;255;235;59",
    "danger": "38;2;255;82;82",
    "info": "38;2;0;229;255",
    "accent": "38;2;255;152;0",
    "muted": "38;2;120;144;156",
    "title": "1;38;2;255;255;255",
    "bold": "1",
    "dim": "2",
}

RISK_ROLES = {
    "SAFE": "ok",
    "RECOMMENDED": "ok",
    "LOW": "ok",
    "ADVANCED": "warn",
    "MEDIUM": "warn",
    "EXPERT": "accent",
    "HIGH": "accent",
    "UNSAFE": "danger",
    "ULTRA": "danger",
    "BLOCKED": "danger",
}

RISK_GLYPHS = {
    "SAFE": "[SAFE]",
    "RECOMMENDED": "[REC]",
    "LOW": "[LOW]",
    "ADVANCED": "[ADV]",
    "MEDIUM": "[MED]",
    "EXPERT": "[EXP]",
    "HIGH": "[HIGH]",
    "UNSAFE": "[UNSAFE]",
    "ULTRA": "[ULTRA]",
    "BLOCKED": "[BLOCKED]",
}


class Theme(object):
    """Resolved palette. When `plain` is true every role renders as ''."""

    def __init__(self, depth="truecolor", plain=False, preset="neon"):
        self.plain = plain or depth == "none"
        self.depth = "none" if self.plain else depth
        self.preset = preset if preset in PRESETS else "neon"
        if self.plain:
            self._table = {}
        elif depth == "truecolor":
            self._table = dict(PRESETS[self.preset])
            self._table.update({"bold": "1", "dim": "2"})
        elif depth == "256":
            self._table = _X256
        else:
            self._table = _BASIC

    # -- roles -------------------------------------------------------------
    def _code(self, role):
        if self.plain:
            return ""
        code = self._table.get(role)
        if not code:
            return ""
        return "\033[" + code + "m"

    @property
    def reset(self):
        return "" if self.plain else RESET

    @property
    def ok(self):
        return self._code("ok")

    @property
    def warn(self):
        return self._code("warn")

    @property
    def danger(self):
        return self._code("danger")

    @property
    def info(self):
        return self._code("info")

    @property
    def accent(self):
        return self._code("accent")

    @property
    def muted(self):
        return self._code("muted")

    @property
    def title(self):
        return self._code("title")

    @property
    def bold(self):
        return self._code("bold")

    @property
    def dim(self):
        return self._code("dim")

    # -- helpers -----------------------------------------------------------
    def paint(self, text, role):
        """Wrap text in a role colour, restoring the previous state after."""
        if self.plain or not text:
            return text
        code = self._code(role)
        if not code:
            return text
        return code + text + self.reset

    def risk(self, tier):
        """Colour a risk tier name using the shared risk map."""
        return self.paint(tier, RISK_ROLES.get(str(tier).upper(), "muted"))

    def risk_glyph(self, tier):
        """ASCII-safe risk badge text (never colour-only)."""
        key = str(tier).upper()
        return RISK_GLYPHS.get(key, "[" + key + "]")


def make_theme(caps=None):
    """Build a Theme from resolved capabilities."""
    if caps is None:
        from . import term

        caps = term.caps()
    import os

    return Theme(depth=caps.color_depth, plain=caps.no_color,
                 preset=os.environ.get("ALFI_THEME", "neon"))
