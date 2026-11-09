"""
scripts/ui/widgets.py - Pure rendering helpers (stdlib only).

Every function here takes plain data plus an explicit width and theme and
returns strings. No I/O, no globals, no terminal probing: that makes the whole
visual layer snapshot-testable, which is the point of the refactor.

The one non-obvious piece is display_width(): Python's len() counts code
points, but a terminal draws an emoji in two cells and an ANSI escape in none.
Padding with len() is what made the old cards ragged (a "74-wide" menu rendered
92 columns). Everything that pads goes through display_width().
"""

from __future__ import annotations

import re
import unicodedata

ANSI_RE = re.compile(r"\033\[[0-9;]*[a-zA-Z]")

# Emoji and pictograph blocks that terminals draw double-width.
_WIDE_RANGES = (
    (0x1F000, 0x1FAFF),  # emoji, symbols, pictographs, regional flags
    (0x2600, 0x27BF),    # misc symbols and dingbats (⚡ ⚠ ✅ …)
    (0x2B00, 0x2BFF),    # arrows and geometric shapes used as icons
    (0xFE00, 0xFE0F),    # variation selectors (zero-width, handled separately)
)

# Symbols that sit inside the ranges above but that terminals render one cell
# wide in practice. Listing them keeps borders aligned on the common terminals.
_NARROW_EXCEPTIONS = frozenset(
    (0x2713, 0x2714, 0x2717, 0x2718, 0x2726, 0x2727, 0x2605, 0x2606)
)

GLYPHS_UNICODE = {
    "tl": "\u256d", "tr": "\u256e", "bl": "\u2570", "br": "\u256f",
    "h": "\u2500", "v": "\u2502", "dot": "\u25cf", "arrow": "\u2192",
    "ok": "\u2714", "fail": "\u2716", "skip": "\u21b7", "warn": "\u26a0",
    "bullet": "\u2022", "ellipsis": "\u2026",
}

GLYPHS_ASCII = {
    "tl": "+", "tr": "+", "bl": "+", "br": "+",
    "h": "-", "v": "|", "dot": "*", "arrow": "->",
    "ok": "OK", "fail": "XX", "skip": "--", "warn": "!!",
    "bullet": "*", "ellipsis": "...",
}


def glyphs(unicode_ok=True):
    """Border and status glyph set for this terminal."""
    return GLYPHS_UNICODE if unicode_ok else GLYPHS_ASCII


def strip_ansi(text):
    """Remove ANSI escape sequences."""
    return ANSI_RE.sub("", text or "")


def _is_wide(cp):
    if cp in _NARROW_EXCEPTIONS:
        return False
    for lo, hi in _WIDE_RANGES:
        if lo <= cp <= hi:
            return True
    return False


def display_width(text):
    """Visible column width: ignores ANSI, counts emoji/CJK as two cells."""
    clean = strip_ansi(text or "")
    total = 0
    i = 0
    n = len(clean)
    while i < n:
        ch = clean[i]
        cp = ord(ch)
        if cp in (0xFE0E, 0xFE0F, 0x200D):  # variation selectors / ZWJ
            i += 1
            continue
        if unicodedata.combining(ch):
            i += 1
            continue
        wide = unicodedata.east_asian_width(ch) in ("W", "F") or _is_wide(cp)
        if i + 1 < n and ord(clean[i + 1]) == 0xFE0F:
            wide = True
        total += 2 if wide else 1
        i += 1
    return total


def truncate(text, width, ellipsis="\u2026"):
    """Cut text to `width` visible columns, appending an ellipsis if cut."""
    if width <= 0:
        return ""
    if display_width(text) <= width:
        return text
    ell_w = display_width(ellipsis)
    budget = max(0, width - ell_w)
    out = []
    used = 0
    for ch in strip_ansi(text):
        w = display_width(ch)
        if used + w > budget:
            break
        out.append(ch)
        used += w
    return "".join(out) + ellipsis


def pad(text, width, align="left"):
    """Pad to exactly `width` visible columns."""
    text = truncate(text, width) if display_width(text) > width else text
    gap = max(0, width - display_width(text))
    if align == "right":
        return " " * gap + text
    if align == "center":
        left = gap // 2
        return " " * left + text + " " * (gap - left)
    return text + " " * gap


def rule(width, theme=None, char="\u2500"):
    """A horizontal separator of exactly `width` columns."""
    line = char * max(0, width)
    return theme.paint(line, "muted") if theme else line


def box(lines, width, theme=None, glyph=None, title=None, pad_x=1):
    """Wrap pre-rendered lines in a rounded border of exactly `width` columns."""
    g = glyph or GLYPHS_UNICODE
    inner = max(4, width - 2)
    body_width = inner - (pad_x * 2)

    out = []
    if title:
        label = " " + title + " "
        fill = max(0, inner - display_width(label) - 1)
        head = g["h"] + label + g["h"] * fill
        head = truncate(head, inner)
        head = pad(head, inner)
        top = g["tl"] + head + g["tr"]
    else:
        top = g["tl"] + g["h"] * inner + g["tr"]
    out.append(theme.paint(top, "muted") if theme else top)

    for line in lines:
        content = pad(line, body_width)
        row = g["v"] + (" " * pad_x) + content + (" " * pad_x) + g["v"]
        out.append(theme.paint(row, "muted") if theme else row)

    bottom = g["bl"] + g["h"] * inner + g["br"]
    out.append(theme.paint(bottom, "muted") if theme else bottom)
    return out


def kv_rows(pairs, label_width=None, theme=None, sep=":"):
    """Render [(label, value), ...] as aligned 'label : value' lines."""
    if label_width is None:
        label_width = max([display_width(str(k)) for k, _ in pairs] or [0])
    rows = []
    for label, value in pairs:
        lab = pad(str(label), label_width)
        if theme:
            lab = theme.paint(lab, "muted")
        rows.append(lab + " " + sep + " " + str(value))
    return rows


def badge(tier, theme=None, glyph=None):
    """Risk badge. Always carries a word, never colour alone."""
    from .theme import RISK_ROLES, RISK_GLYPHS

    key = str(tier).upper()
    label = RISK_GLYPHS.get(key, "[" + key + "]")
    if theme is None or theme.plain:
        return label
    return theme.paint(label, RISK_ROLES.get(key, "muted"))


def bar(value, maximum, width, theme=None, role="ok", glyph=None):
    """Horizontal bar: [#####-----] 62%"""
    g = glyph or GLYPHS_UNICODE
    full_ch = "#" if g["h"] == "-" else "\u2588"
    empty_ch = "-" if g["h"] == "-" else "\u2591"
    try:
        ratio = 0.0 if not maximum else max(0.0, min(1.0, float(value) / float(maximum)))
    except (TypeError, ValueError, ZeroDivisionError):
        ratio = 0.0
    filled = int(round(ratio * width))
    body = full_ch * filled + empty_ch * (width - filled)
    if theme and not theme.plain:
        body = theme.paint(full_ch * filled, role) + theme.paint(empty_ch * (width - filled), "muted")
    return "[" + body + "] " + str(int(round(ratio * 100))) + "%"


def status_line(items, width, theme=None, glyph=None, sep=" \u00b7 "):
    """One-line device status header, truncated to the terminal width."""
    g = glyph or GLYPHS_UNICODE
    dot = g["dot"] + " "
    parts = []
    for item in items:
        if item:
            parts.append(dot + str(item))
            dot = sep
    line = "".join(parts).strip()
    return truncate(line, width)


def table(headers, rows, widths, theme=None):
    """Fixed-width column table; cells are truncated, never wrapped."""
    out = []
    head = "  ".join(pad(str(h), w) for h, w in zip(headers, widths))
    out.append(theme.paint(head, "muted") if theme else head)
    out.append(("-" * display_width(head)))
    for row in rows:
        cells = []
        for cell, w in zip(row, widths):
            cells.append(pad(str(cell), w))
        line = "  ".join(cells)
        out.append(line)
    return out


def progress_bar(done, total, width, theme=None, label=""):
    """Determinate progress line: [####----] 6/10  label"""
    total = max(1, int(total))
    done = max(0, min(int(done), total))
    inner = max(6, width - len("[] 100%  ") - 12)
    filled = int(round(inner * done / float(total)))
    g = glyphs(theme is None or not theme.plain)
    full_ch = "#" if g["h"] == "-" else "\u2588"
    empty_ch = "-" if g["h"] == "-" else "\u2591"
    body = full_ch * filled + empty_ch * (inner - filled)
    if theme and not theme.plain:
        body = theme.paint(full_ch * filled, "ok") + theme.paint(empty_ch * (inner - filled), "muted")
    line = "[" + body + "] " + str(done) + "/" + str(total)
    if label:
        line += "  " + truncate(str(label), max(8, width - display_width(line) - 2))
    return line


SPARK_CHARS = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"   # ▁▂▃▄▅▆▇█
SPARK_ASCII = "._-~=*#@"


def sparkline(values, width=None, theme=None, role="ok", ascii_mode=False):
    """Render a series as block glyphs. Always exactly `width` cells when given."""
    chars = SPARK_ASCII if ascii_mode else SPARK_CHARS
    series = [float(v) for v in (values or []) if v is not None]
    if not series:
        return " " * (width or 0)
    if width and len(series) > width:
        # Downsample by averaging buckets so the shape survives.
        step = len(series) / float(width)
        series = [
            sum(series[int(i * step):max(int((i + 1) * step), int(i * step) + 1)])
            / max(1, len(series[int(i * step):max(int((i + 1) * step), int(i * step) + 1)]))
            for i in range(width)
        ]
    low, high = min(series), max(series)
    span = (high - low) or 1.0
    out = []
    for value in series:
        index = int(round((value - low) / span * (len(chars) - 1)))
        out.append(chars[max(0, min(len(chars) - 1, index))])
    text = "".join(out)
    if width:
        text = pad(text, width)
    return theme.paint(text, role) if theme else text


def gauge(value, maximum, width=20, theme=None, label="", unit="", ascii_mode=False):
    """A labelled meter: LABEL [#####-----] 62%  12.3/16.0 GB"""
    try:
        ratio = 0.0 if not maximum else max(0.0, min(1.0, float(value) / float(maximum)))
    except (TypeError, ValueError, ZeroDivisionError):
        ratio = 0.0
    role = "ok" if ratio < 0.7 else ("warn" if ratio < 0.9 else "danger")
    full_ch = "#" if ascii_mode else "\u2588"
    empty_ch = "-" if ascii_mode else "\u2591"
    filled = int(round(ratio * width))
    body = full_ch * filled + empty_ch * (width - filled)
    if theme and not theme.plain:
        body = theme.paint(full_ch * filled, role) + theme.paint(empty_ch * (width - filled), "muted")
    head = pad(label, 10) + " " if label else ""
    tail = " %3d%%" % int(round(ratio * 100))
    if unit:
        tail += "  " + unit
    return head + "[" + body + "]" + tail


def gradient(text, start=(0, 230, 118), end=(0, 229, 255), plain=False):
    """Truecolour sweep across a string. Plain mode returns the text unchanged."""
    if plain or not text:
        return text
    clean = strip_ansi(text)
    chars = [c for c in clean if display_width(c)]
    span = max(1, len(chars) - 1)
    out = []
    index = 0
    for ch in clean:
        if not display_width(ch):
            out.append(ch)
            continue
        t = index / float(span)
        r = int(start[0] + (end[0] - start[0]) * t)
        g = int(start[1] + (end[1] - start[1]) * t)
        b = int(start[2] + (end[2] - start[2]) * t)
        out.append("\033[38;2;%d;%d;%dm%s" % (r, g, b, ch))
        index += 1
    return "".join(out) + "\033[0m"


def panel(lines, width, theme=None, title=None, ascii_mode=False):
    """Double-ruled frame for the 'graphics' surfaces (live monitor, results)."""
    if ascii_mode:
        tl, tr, bl, br, h, v = "+", "+", "+", "+", "=", "|"
    else:
        tl, tr, bl, br, h, v = "\u2554", "\u2557", "\u255a", "\u255d", "\u2550", "\u2551"
    inner = max(4, width - 2)
    if title:
        label = " " + title + " "
        head = h + label + h * max(0, inner - display_width(label) - 1)
        top = tl + pad(head, inner) + tr
    else:
        top = tl + h * inner + tr
    out = [theme.paint(top, "muted") if theme else top]
    for line in lines:
        row = v + " " + pad(line, inner - 2) + " " + v
        out.append(theme.paint(row, "muted") if theme else row)
    bottom = bl + h * inner + br
    out.append(theme.paint(bottom, "muted") if theme else bottom)
    return out
