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
import json
import sys

import config

# command -> module in scripts/ . None means handled in this file.
COMMANDS = {
    "tui": "wizard",
    "status": None,
    "watch": "monitor",
    "probe": "probe",
    "attrib": "attrib",
    "verify": "verify",
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
    "help": None,
}

def render_help():
    """Grouped command reference, generated from helpdata so it cannot drift."""
    import helpdata

    lines = ["usage: alfi [command] [options]", ""]
    for group, entries in helpdata.grouped():
        lines.append(group.upper())
        for entry in entries:
            lines.append("  " + helpdata.summary_line(entry))
        lines.append("")
    lines.append("  * changes the device - pair it with --dry-run first")
    lines.append("  alfi help <command> for what one command reads or changes")
    return "\n".join(lines)


HELP = None  # built by render_help(); kept so older imports do not break



def status(argv):
    """One line: device, platform, transport, battery, and the saved default mode."""
    want_json = "--json" in (argv or [])
    from connect import get_connected_devices, get_device_info, run_adb
    from ui import ui as get_ui

    u = get_ui()
    cfg = config.load()
    devices = get_connected_devices()
    authorised = [d for d in devices if d.get("status") == "device"]

    if not authorised:
        pending = [d for d in devices if d.get("status") != "device"]
        line = "no device" + (" (one unauthorized, tap Allow)" if pending else "")
        if want_json:
            print(json.dumps({"connected": False, "pending": len(pending)}, indent=2))
        else:
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
    if want_json:
        print(json.dumps({
            "connected": True,
            "serial": serial,
            "brand": info.get("brand"),
            "model": info.get("model"),
            "android": info.get("android_version"),
            "sdk": info.get("sdk_level"),
            "transport": transport,
            "battery": battery or None,
            "devices": len(authorised),
            "default_mode": cfg.get("mode"),
        }, indent=2))
        return 0
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
    if not argv or argv[0] in ("-h", "--help"):
        if argv:
            entry = __import__("helpdata").by_name("config")
            u.print(u.box(__import__("helpdata").detail_lines(entry, u.width - 4), title="CONFIG"))
            return 0
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


def help_command(argv):
    """`alfi help` (grouped list) or `alfi help <command>` (full detail)."""
    import helpdata
    from ui import ui as get_ui

    if not argv or argv[0] in ("-h", "--help"):
        print(render_help())
        return 0
    if argv[0] == "--json":
        print(json.dumps(helpdata.COMMANDS, indent=2))
        return 0

    name = argv[0].lower()
    entry = helpdata.by_name(name)
    if entry is None:
        print("alfi: no help for '%s'" % name, file=sys.stderr)
        close = [c["name"] for c in helpdata.COMMANDS if c["name"].startswith(name[:3])]
        if close:
            print("did you mean: " + ", ".join(close[:5]), file=sys.stderr)
        return 2

    ui = get_ui()
    ui.print(ui.box(helpdata.detail_lines(entry, ui.width - 4), title=name.upper()))
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cfg = config.load()
    config.apply_to_env(cfg)

    if not argv:
        return dispatch("wizard", [], cfg)

    command, rest = argv[0], argv[1:]
    if command in ("-h", "--help"):
        print(render_help())
        return 0
    if command == "help":
        return help_command(rest)
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
        print(render_help(), file=sys.stderr)
        return 2
    return dispatch(module_name, rest, cfg)


if __name__ == "__main__":
    sys.exit(main())
