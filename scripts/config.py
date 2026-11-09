"""
scripts/config.py - Persisted user defaults for the `alfi` command.

One JSON file, no schema library. Everything is optional; a missing file or a
bad key falls back to the defaults so the CLI never fails because of config.
"""

from __future__ import annotations

import json
import os

DEFAULTS = {
    "device": None,     # default serial / IP:port
    "mode": None,       # default --mode for `alfi modes`
    "color": "auto",    # auto | always | never
    "ascii": False,     # force ASCII glyphs
    "theme": "neon",    # neon | amber | mono
    "user": 0,          # default Android user profile
}

VALID_KEYS = tuple(DEFAULTS)


def config_path():
    """$ALFI_CONFIG, else $XDG_CONFIG_HOME/alfi/config.json, else ~/.config/alfi/config.json."""
    override = os.environ.get("ALFI_CONFIG")
    if override:
        return override
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "alfi", "config.json")


def load():
    """Read the config, merged over defaults. Never raises."""
    data = dict(DEFAULTS)
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            stored = json.load(f)
        if isinstance(stored, dict):
            for key, value in stored.items():
                if key in DEFAULTS:
                    data[key] = value
    except (OSError, ValueError):
        pass
    return data


def save(data):
    """Write the config, creating the directory. Returns the path."""
    path = config_path()
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    clean = {k: data[k] for k in VALID_KEYS if k in data}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2)
        f.write("\n")
    return path


def set_value(key, value):
    """Set one key and persist. Returns (ok, message)."""
    if key not in DEFAULTS:
        return False, "unknown key '%s' (valid: %s)" % (key, ", ".join(VALID_KEYS))
    data = load()
    if value in ("", "none", "null", "unset"):
        data[key] = DEFAULTS[key]
    elif isinstance(DEFAULTS[key], bool):
        data[key] = str(value).lower() in ("1", "true", "yes", "on")
    elif isinstance(DEFAULTS[key], int):
        try:
            data[key] = int(value)
        except ValueError:
            return False, "'%s' expects a number" % key
    else:
        data[key] = value
    path = save(data)
    return True, "%s = %r  (%s)" % (key, data[key], path)


def apply_to_env(data):
    """Project the config onto the env vars the rest of the tool already reads."""
    if data.get("device"):
        os.environ["ANDROID_SERIAL"] = str(data["device"])
    if data.get("ascii"):
        os.environ["ALFI_ASCII"] = "1"
    if data.get("theme"):
        os.environ["ALFI_THEME"] = str(data["theme"])
    if data.get("color") == "never":
        os.environ["NO_COLOR"] = "1"
    elif data.get("color") == "always":
        os.environ.pop("NO_COLOR", None)
