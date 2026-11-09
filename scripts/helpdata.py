"""
scripts/helpdata.py - the single source of truth for what every command does.

Both `alfi help` and the dashboard's help screen render from this table, so a
command cannot exist without an explanation, and the explanation cannot drift
between the two surfaces. `tests/test_helpdata.py` fails if a script has no
entry here.

Fields:
  name      subcommand as typed after `alfi`
  group     which help section it belongs to
  summary   one line, imperative, what it does
  detail    2-3 lines: what it reads or changes, and when to reach for it
  example   a copy-pasteable invocation
  mutates   True if it can change the device
"""

from __future__ import annotations

GROUPS = ["Measure", "Optimise", "Recover", "Maintain", "Core"]

COMMANDS = [
    # ---------------------------------------------------------------- measure
    {
        "name": "probe",
        "group": "Measure",
        "summary": "Measure what the phone is actually waiting on",
        "detail": "Reads /proc/pressure (PSI) for memory, IO and CPU stall time, the thermal "
                  "status, real memory use and battery in one round-trip. Prints a plain "
                  "verdict such as 'memory is not the problem' instead of a bare RAM percentage. "
                  "Falls back to /proc/vmstat and says so on kernels without PSI.",
        "example": "alfi probe",
        "mutates": False,
    },
    {
        "name": "attrib",
        "group": "Measure",
        "summary": "Name the culprit behind the stalls",
        "detail": "Ranks processes by resident memory and flags one eating a quarter of RAM, "
                  "lists which apps are still interpreted (dexopt status=verify), and counts "
                  "wakeups per package. Run it after probe tells you there is pressure.",
        "example": "alfi attrib",
        "mutates": False,
    },
    {
        "name": "diagnose",
        "group": "Measure",
        "summary": "Classic CPU, load-average and process report",
        "detail": "Load averages, top CPU processes and memory pressure in the older format. "
                  "Kept for continuity; probe is the better starting point on Android 10+.",
        "example": "alfi diagnose",
        "mutates": False,
    },
    {
        "name": "bench",
        "group": "Measure",
        "summary": "Frame pacing benchmark (jank %, p90/p99, 1% low)",
        "detail": "Resets gfxinfo, drives a fixed scroll, then parses framestats. The jank "
                  "threshold follows the panel's refresh rate, so a 120 Hz phone is judged "
                  "against 9.6 ms, not 19.1 ms.",
        "example": "alfi bench --app com.android.settings",
        "mutates": False,
    },
    {
        "name": "power",
        "group": "Measure",
        "summary": "Battery drain and wakelock audit",
        "detail": "Parses batterystats for partial wakelocks, screen-off time and computed "
                  "drain. Reports 'unrecorded' rather than 0.0 when the dump is empty.",
        "example": "alfi power --audit",
        "mutates": False,
    },
    {
        "name": "watch",
        "group": "Measure",
        "summary": "Live monitor: CPU, memory, swap/zram, battery, top process",
        "detail": "Redraws a panel every interval with meters and a CPU sparkline. Piped or "
                  "redirected it prints one snapshot and exits, so it is safe in logs and CI.",
        "example": "alfi watch --interval 3",
        "mutates": False,
    },
    {
        "name": "status",
        "group": "Core",
        "summary": "One line: device, Android, transport, battery, default mode",
        "detail": "The fastest way to confirm adb sees the phone and which target is active.",
        "example": "alfi status",
        "mutates": False,
    },

    # --------------------------------------------------------------- optimise
    {
        "name": "modes",
        "group": "Optimise",
        "summary": "Four-tier optimisation with a pre-flight gate",
        "detail": "Low/Medium/High/Ultra. Shows exactly what will be disabled, writes an "
                  "fsynced rollback manifest before the first change, then applies. Ultra "
                  "requires typing I UNDERSTAND. Every package goes through the allowlist "
                  "and dependency graph first.",
        "example": "alfi modes --mode medium --dry-run",
        "mutates": True,
    },
    {
        "name": "optimize",
        "group": "Optimise",
        "summary": "Classic OEM debloater (profile-based)",
        "detail": "The original debloat path: picks packages for the detected OEM profile and "
                  "disables them. modes is the guided version of the same work.",
        "example": "alfi optimize --dry-run",
        "mutates": True,
    },
    {
        "name": "compile",
        "group": "Optimise",
        "summary": "AOT-compile apps, or only the ones still interpreted",
        "detail": "With --targets it compiles exactly the packages attrib found at "
                  "status=verify. Without it, compiles a list or all user apps. "
                  "speed-profile is profile-guided and the safest default.",
        "example": "alfi compile --targets --dry-run",
        "mutates": True,
    },
    {
        "name": "appops",
        "group": "Optimise",
        "summary": "Restrict background execution for chosen apps",
        "detail": "Sets RUN_IN_BACKGROUND / RUN_ANY_IN_BACKGROUND to ignore and moves the app "
                  "to the restricted standby bucket. Reversible from the written manifest.",
        "example": "alfi appops --preset social --dry-run",
        "mutates": True,
    },
    {
        "name": "doze",
        "group": "Optimise",
        "summary": "Audit or clean the DeviceIdle battery allowlist",
        "detail": "Lists who is exempt from Doze, splits system from user exemptions "
                  "correctly, and can remove the user-granted ones. System exemptions are "
                  "reported, not touched.",
        "example": "alfi doze --clean --dry-run",
        "mutates": True,
    },
    {
        "name": "ui",
        "group": "Optimise",
        "summary": "Animation scale and system cache trim",
        "detail": "Sets window/transition/animator scales (0.5x is the usual sweet spot) and "
                  "trims stale caches. Fails loudly instead of pretending when no device is "
                  "attached.",
        "example": "alfi ui --scale 0.5 --dry-run",
        "mutates": True,
    },

    # ---------------------------------------------------------------- recover
    {
        "name": "verify",
        "group": "Recover",
        "summary": "Did the debloat survive a reboot?",
        "detail": "Compares the newest manifest with live device state and names every package "
                  "an OEM update quietly restored. --baseline records boot_id plus current "
                  "states so a reboot can be proven rather than assumed.",
        "example": "alfi verify --baseline   then   alfi verify",
        "mutates": False,
    },
    {
        "name": "restore",
        "group": "Recover",
        "summary": "Roll back packages from a manifest",
        "detail": "Re-enables (or reinstalls) everything recorded in a snapshot. Restores the "
                  "APK; app data removed by an uninstall cannot come back.",
        "example": "alfi restore --manifest latest",
        "mutates": True,
    },
    {
        "name": "rescue",
        "group": "Recover",
        "summary": "Emergency recovery for broken services",
        "detail": "Lists disabled packages, re-enables critical components and prints per-OEM "
                  "safe-mode guidance. Use it when the phone misbehaves after a debloat.",
        "example": "alfi rescue --list-disabled",
        "mutates": True,
    },
    {
        "name": "audit",
        "group": "Recover",
        "summary": "Security and malware audit",
        "detail": "Flags accessibility hijackers, device admins, ghost apps without a launcher "
                  "icon and risky permission clusters. Says 'unknown' rather than accusing "
                  "when the dump lacks the fields.",
        "example": "alfi audit",
        "mutates": False,
    },
    {
        "name": "shizuku",
        "group": "Recover",
        "summary": "Export on-device rish scripts",
        "detail": "Writes a shell script you can run in Termux with Shizuku, plus a rollback "
                  "script, so the phone can be tuned later without a PC.",
        "example": "alfi shizuku",
        "mutates": False,
    },

    # --------------------------------------------------------------- maintain
    {
        "name": "update",
        "group": "Maintain",
        "summary": "Refresh the community debloat catalog",
        "detail": "Pulls the upstream UAD list (5,399 packages) and merges it locally, keeping "
                  "your own tier choices and recording upstream's separately.",
        "example": "alfi update",
        "mutates": False,
    },
    {
        "name": "vault",
        "group": "Maintain",
        "summary": "Per-device audit history",
        "detail": "Shows what was changed on each device and when, from devices/<slug>/history.md.",
        "example": "alfi vault",
        "mutates": False,
    },
    {
        "name": "config",
        "group": "Maintain",
        "summary": "Saved defaults (device, mode, theme, colour, ascii, user)",
        "detail": "Defaults are applied as environment variables and injected flags; an explicit "
                  "flag always wins. Stored in ~/.config/alfi/config.json.",
        "example": "alfi config set theme amber",
        "mutates": False,
    },
    {
        "name": "devices",
        "group": "Core",
        "summary": "List attached devices and pairing help",
        "detail": "Shows authorization state and the steps for USB or wireless debugging.",
        "example": "alfi devices",
        "mutates": False,
    },
    {
        "name": "tui",
        "group": "Core",
        "summary": "Interactive dashboard",
        "detail": "The menu-driven front end over every command here. Press H inside it for "
                  "this same reference.",
        "example": "alfi",
        "mutates": False,
    },
    {
        "name": "help",
        "group": "Core",
        "summary": "This reference",
        "detail": "alfi help lists everything grouped by purpose; alfi help <command> explains "
                  "one command in full.",
        "example": "alfi help probe",
        "mutates": False,
    },
]


def by_name(name):
    for entry in COMMANDS:
        if entry["name"] == name:
            return entry
    return None


def grouped():
    """[(group, [entries])] in GROUPS order, empty groups dropped."""
    out = []
    for group in GROUPS:
        items = [c for c in COMMANDS if c["group"] == group]
        if items:
            out.append((group, items))
    return out


def summary_line(entry):
    """One-line form: name, summary, and a marker when it changes the device."""
    flag = " *" if entry["mutates"] else ""
    return "%-9s %s%s" % (entry["name"], entry["summary"], flag)


def detail_lines(entry, width=74):
    """Wrapped detail for one command, as a list of lines."""
    import textwrap

    lines = [entry["summary"], ""]
    lines.extend(textwrap.wrap(entry["detail"], width=max(20, width)))
    lines.append("")
    lines.append("example: " + entry["example"])
    lines.append("changes the device: " + ("yes" if entry["mutates"] else "no"))
    return lines
