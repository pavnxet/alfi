#!/usr/bin/env python3
"""
scripts/cli.py - the single `alfi` entry point.

Every capability of the toolkit is reachable as `alfi <command> [flags]`. The
command table maps one name to one existing script, and dispatch works by
setting sys.argv and calling that script's main(), so nothing is reimplemented
here and every flag the scripts already accept keeps working.

    alfi                      open the interactive dashboard
    alfi status               one-line device status
    alfi modes --mode low     pre-flight, confirm, apply
    alfi bench --app com.android.settings
    alfi config set mode medium
"""

from __future__ import annotations

import importlib
import sys

import config

# command -> module in scripts/ . None means handled in this file.
COMMANDS = {
    "tui": "wizard",
    "status": None,
    "watch": "monitor",
    "devices": "connect",
    "modes": "modes",
    "optimize": "optimize",
    "diagnose": "diagnose",
    "bench": "bench",
    "power": "power_audit",
    "doze": "doze_boost",
    "compile": "compile_speed",
    "appops": "appops_restrict",
    "ui": "tweak_ui",
    "audit": "security_audit",
    "shizuku": "export_shizuku",
    "rescue": "rescue",
    "restore": "restore",
    "vault": "device_tracker",
    "update": "update_database",
    "config": None,
}

HELP = """usage: alfi [command] [options]

  alfi                       interactive dashboard (default)
  alfi status                one-line device status
  alfi watch                 live CPU / memory / swap / battery monitor
  alfi devices               list attached devices and pairing help

  alfi modes   [--mode low|medium|high|ultra] [--dry-run] [--yes]
  alfi optimize [--dry-run]  classic OEM debloater
  alfi diagnose              CPU, memory pressure and zRAM report
  alfi bench   [--app PKG]   frame pacing benchmark
  alfi power                 batterystats and wakelock audit
  alfi doze    [--clean]     DeviceIdle allowlist audit
  alfi compile [--filter speed] ART pre-compile
  alfi appops  [--preset social] background AppOps limits
  alfi ui      [--scale 0.5] animation scale and cache trim
  alfi audit                 security and malware audit
  alfi shizuku               export on-device rish scripts
  alfi rescue  [--list-disabled] emergency recovery
  alfi restore [--manifest latest] rollback
  alfi vault                 per-device audit history
  alfi update                refresh the community debloat catalog

  alfi config                show saved defaults
  alfi config set KEY VALUE  device | mode | color | ascii | user
  alfi config path           where defaults are stored

Every command passes its remaining flags straight to the underlying script, so
`alfi diagnose --json`, `alfi modes --dry-run` and so on all work.
"""


def status(argv):
    """One line: device, platform, transport, battery, and the saved default mode."""
    from connect import get_connected_devices, get_device_info, run_adb
    from ui import ui as get_ui

    u = get_ui()
    cfg = config.load()
    devices = get_connected_devices()
    authorised = [d for d in devices if d.get("status") == "device"]

    if not authorised:
        pending = [d for d in devices if d.get("status") != "device"]
        line = "no device" + (" (one unauthorized, tap Allow)" if pending else "")
        u.print(u.status([line]))
        return 1 if pending else 0

    serial = authorised[0]["serial"]
    info = get_device_info(serial)
    ok, level = run_adb(["-s", serial, "shell", "dumpsys battery | grep -m1 level"], timeout=5)
    battery = ""
    if ok and level:
        import re as _re
        match = _re.search(r"level:\s*(\d+)", level)
        if match:
            battery = match.group(1) + "%"

    transport = "wireless" if ":" in serial else "usb"
    u.print(u.status([
        "%s %s" % (str(info.get("brand", "?")).upper(), info.get("model", "?")),
        "Android %s (SDK %s)" % (info.get("android_version", "?"), info.get("sdk_level", "?")),
        transport,
        battery,
        "%d attached" % len(authorised) if len(authorised) > 1 else "",
        "default mode: %s" % cfg["mode"] if cfg.get("mode") else "",
    ]))
    return 0


def config_command(argv):
    """`alfi config`, `alfi config set KEY VALUE`, `alfi config path`."""
    from ui import ui as get_ui

    u = get_ui()
    if not argv:
        data = config.load()
        rows = ["%s = %r" % (k, data[k]) for k in config.VALID_KEYS]
        u.print(u.box(rows, title="ALFI DEFAULTS: " + config.config_path()))
        return 0
    action = argv[0]
    if action == "path":
        u.print(config.config_path())
        return 0
    if action == "set":
        if len(argv) < 3:
            u.print("usage: alfi config set KEY VALUE")
            return 2
        ok, message = config.set_value(argv[1], " ".join(argv[2:]))
        u.print(message)
        return 0 if ok else 2
    if action == "get" and len(argv) >= 2:
        u.print(repr(config.load().get(argv[1])))
        return 0
    u.print("usage: alfi config [set KEY VALUE | get KEY | path]")
    return 2


def with_defaults(module_name, argv, cfg):
    """Append saved defaults where they are unambiguous and the flag is absent."""
    argv = list(argv)
    if module_name == "modes" and cfg.get("mode") and "--mode" not in argv:
        argv += ["--mode", str(cfg["mode"])]
    if cfg.get("user") and "--user" not in argv and module_name in ("modes", "restore", "optimize"):
        argv += ["--user", str(cfg["user"])]
    return argv


def dispatch(module_name, argv, cfg):
    """Run a script's main() with argv rewritten. Restores sys.argv afterwards."""
    argv = with_defaults(module_name, argv, cfg)

    module = importlib.import_module(module_name)
    main = getattr(module, "main", None)
    if main is None:
        print("alfi: %s has no main()" % module_name, file=sys.stderr)
        return 2

    saved = sys.argv
    sys.argv = [module_name] + argv
    try:
        result = main()
        return result if isinstance(result, int) else 0
    finally:
        sys.argv = saved


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cfg = config.load()
    config.apply_to_env(cfg)

    if not argv:
        return dispatch("wizard", [], cfg)

    command, rest = argv[0], argv[1:]
    if command in ("-h", "--help", "help"):
        print(HELP)
        return 0
    if command in ("-V", "--version"):
        try:
            from __init__ import __version__
        except ImportError:
            from scripts import __version__  # type: ignore
        print("alfi %s" % __version__)
        return 0

    # Any other leading flag means "dashboard with these options" (`alfi --action modes`).
    if command.startswith("-"):
        return dispatch("wizard", argv, cfg)

    if command == "status":
        return status(rest)
    if command == "config":
        return config_command(rest)

    module_name = COMMANDS.get(command)
    if module_name is None:
        print("alfi: unknown command '%s'\n" % command, file=sys.stderr)
        print(HELP)
        return 2
    return dispatch(module_name, rest, cfg)


if __name__ == "__main__":
    sys.exit(main())
