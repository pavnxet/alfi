"""
scripts/ui/prompts.py - One validated input path for the whole UI.

Rules that keep the existing tests and scripts working:

* `input()` is called by name (resolved from builtins at call time), so
  `patch("builtins.input", ...)` keeps working exactly as before.
* Each helper consumes at most one line per attempt, matching the call counts
  the current suite asserts on.
* EOF and Ctrl-C never raise: they return None so the caller can cancel
  cleanly instead of printing a traceback.
"""

from __future__ import annotations

from . import keys


def read_line(prompt_text="", default=""):
    """Read one line. Returns None on EOF/Ctrl-C. Empty input yields `default`."""
    try:
        value = input(prompt_text)
    except (EOFError, KeyboardInterrupt):
        return None
    if value is None:
        return None
    value = value.strip()
    return value if value else default


def ask(prompt_text, valid=None, default=None, normalise=str.upper):
    """Read one line and validate it against `valid` (a set of accepted values).

    One prompt per call: callers that need retries loop themselves, so the
    number of input() calls stays predictable and testable.
    """
    value = read_line(prompt_text, default=default or "")
    if value is None:
        return None
    if normalise:
        value = normalise(value)
    if valid is None or value in valid:
        return value
    return None


def confirm(prompt_text="Proceed? [y/N]: ", default="n"):
    """Yes/no confirmation. Returns True only for an explicit yes."""
    value = read_line(prompt_text, default=default)
    if value is None:
        return False
    return value.strip().lower() in ("y", "yes")


def typed_gate(word, prompt_text=None):
    """Require the user to type an exact phrase (Ultra safety gate)."""
    prompt_text = prompt_text or ("Type '%s' to confirm: " % word)
    value = read_line(prompt_text)
    if value is None:
        return False
    return value.strip() == word


def select(options, title="", prompt_text="Select: ", default_index=0, render=None):
    """Arrow-key selector with a line-input fallback.

    `options` is a list of (key, label) pairs. In a raw-capable terminal the
    arrow keys move a cursor and Enter picks; otherwise the caller's numbered
    prompt is used, which is what every script and test relies on today.
    """
    if not keys.raw_available() or not options:
        return None

    index = max(0, min(default_index, len(options) - 1))
    while True:
        if render:
            render(index, options)
        key = keys.read_key()
        if key is None:
            return None
        if key == keys.KEY_UP:
            index = (index - 1) % len(options)
        elif key == keys.KEY_DOWN:
            index = (index + 1) % len(options)
        elif key == keys.KEY_ENTER:
            return options[index][0]
        elif key in (keys.KEY_ESC, "q", "Q"):
            return None
        else:
            for opt_key, _label in options:
                if str(opt_key).lower() == str(key).lower():
                    return opt_key
