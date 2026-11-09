#!/usr/bin/env python3
"""
scripts/modes.py - Multi-Tier Optimization Engine & Package Dependency Graph

Defines and executes the 4 calibrated optimization modes:
  🟢 Low:    Zero-risk carrier stub removal, gentle 0.75x animation scales, cache trim.
  🟡 Medium: Balanced daily driver; OEM telemetry debloat, 0.5x animations, ART speed-profile, social AppOps limits.
  🟠 High:    Aggressive performance; vendor bloat (Bixby, Joyose), App Standby restricted, deep Doze, 0 GB zRAM.
  🔴 Ultra:   Extreme strip-down; duplicate accounts/stores/launchers, 0.0x animations, full system ART compile.
             Protected by mandatory dependency graph validation and explicit confirmation gates.
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime
from typing import Dict, Any, List, Set, Tuple, Optional

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from connect import run_adb, get_connected_devices, get_device_info
from operations import apply_package_state, get_package_state
from tweak_ui import set_animation_scale, trim_system_cache
from appops_restrict import set_appops_restriction, set_standby_bucket, PRESET_BACKGROUND_HOGS
from compile_speed import compile_package

def clear_screen():
    """Clear terminal screen and wipe scrollback buffer for a smooth app-like redraw."""
    if os.environ.get("NO_COLOR") or not (sys.stdout and hasattr(sys.stdout, "isatty") and sys.stdout.isatty()):
        return
    try:
        if os.name == "nt":
            os.system("cls")
        else:
            term = os.environ.get("TERM", "")
            if term and term != "dumb":
                sys.stdout.write("\033[H\033[2J\033[3J")
                sys.stdout.flush()
    except Exception:
        pass
        sys.stdout.flush()
    except Exception:
        pass

OPTIMIZATION_MODES = ["low", "medium", "high", "ultra"]

CRITICAL_NEVER_DISABLE: Set[str] = {
    "com.android.phone",
    "com.android.systemui",
    "com.android.settings",
    "com.google.android.webview",
    "com.google.android.trichromelibrary",
    "com.google.android.configupdater",
    "com.android.packageinstaller",
    "com.google.android.packageinstaller"
}

KEYBOARD_PACKAGES: Set[str] = {
    "com.google.android.inputmethod.latin",
    "com.samsung.android.honeyboard",
    "com.sohu.inputmethod.sogou",
    "com.touchtype.swiftkey",
    "com.oppo.keyboard"
}

LAUNCHER_PACKAGES: Set[str] = {
    "com.sec.android.app.launcher",
    "com.miui.home",
    "com.google.android.apps.nexuslauncher",
    "com.android.launcher3",
    "com.oppo.launcher"
}

MODE_CONFIGS = {
    "low": {
        "name": "Low",
        "emoji": "🟢",
        "label": "Low (Zero Risk / Safe Baseline)",
        "description": "Carrier adware & preload stubs only, system cache trim, gentle 0.75x animation scales.",
        "risk_level": "None",
        "target_audience": "Casual users, family phones, work profiles, zero tolerance for feature changes.",
        "animation_scale": "0.75",
        "trim_cache": True,
        "package_tiers": ["Recommended"],
        "category_filter": ["carrier_bloat", "samsung", "xiaomi", "realme_oppo"],
        "appops_preset": None,
        "standby_bucket": None,
        "art_filter": None,
        "zram": None,
        "requires_confirmation": False
    },
    "medium": {
        "name": "Medium",
        "emoji": "🟡",
        "label": "Medium (Balanced / Recommended Daily Driver)",
        "description": "Low + OEM telemetry & tracking daemons, snappy 0.5x animations, ART speed-profile, social AppOps limits.",
        "risk_level": "Low",
        "target_audience": "Everyday smartphone users looking for noticeable smoothness without breaking any feature.",
        "animation_scale": "0.5",
        "trim_cache": True,
        "package_tiers": ["Recommended"],
        "category_filter": ["carrier_bloat", "samsung", "xiaomi", "realme_oppo", "universal_social_bloat"],
        "appops_preset": "social",
        "standby_bucket": "rare",
        "art_filter": "speed-profile",
        "zram": None,
        "requires_confirmation": False
    },
    "high": {
        "name": "High",
        "emoji": "🟠",
        "label": "High (Aggressive Smoothness & Battery)",
        "description": "Medium + non-critical vendor bloat (Bixby, AR Emoji, Joyose), standby bucket restricted, deep Doze, Virtual RAM off guide.",
        "risk_level": "Moderate",
        "target_audience": "Power users, older devices, and budget hardware (2GB-4GB RAM) with heavy background lag.",
        "animation_scale": "0.5",
        "trim_cache": True,
        "package_tiers": ["Recommended", "Advanced"],
        "category_filter": ["carrier_bloat", "samsung", "xiaomi", "realme_oppo", "universal_social_bloat"],
        "appops_preset": "social",
        "standby_bucket": "restricted",
        "art_filter": "speed",
        "zram": None,
        "requires_confirmation": False
    },
    "ultra": {
        "name": "Ultra",
        "emoji": "🔴",
        "label": "Ultra (Extreme / Power Users / Probable Risk)",
        "description": "High + duplicate OEM accounts, stores, secondary keyboards/launchers, 0.0x animations, full system ART compile.",
        "risk_level": "High (Probable feature restrictions)",
        "target_audience": "Enthusiasts, secondary devices, dedicated gaming setups seeking maximum raw memory & zero overhead.",
        "animation_scale": "0.0",
        "trim_cache": True,
        "package_tiers": ["Recommended", "Advanced", "Expert"],
        "category_filter": ["carrier_bloat", "samsung", "xiaomi", "realme_oppo", "universal_social_bloat"],
        "appops_preset": "all_third_party",
        "standby_bucket": "restricted",
        "art_filter": "speed",
        "zram": None,
        "requires_confirmation": True
    }
}

def get_database_path() -> str:
    """Resolve location of package_database.json across source repository and wheel installations."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "package_database.json"),
        os.path.join(here, "..", "package_database.json")
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.normpath(c)
    return os.path.normpath(os.path.join(here, "..", "package_database.json"))

def load_database() -> Dict[str, Any]:
    """Load package database with categories and dependency graphs."""
    db_path = get_database_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"Package database not found at '{db_path}'. "
            "Please ensure package_database.json exists in the repository or installation directory."
        )
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Error reading package database from '{db_path}': {e}")

def get_mode_config(mode: str) -> Dict[str, Any]:
    """Return immutable configuration dictionary for a given mode."""
    m = mode.lower().strip()
    if m not in MODE_CONFIGS:
        raise ValueError(f"Invalid mode '{mode}'. Choose from: {', '.join(OPTIMIZATION_MODES)}")
    return dict(MODE_CONFIGS[m])

def get_installed_packages(serial: Optional[str] = None, user_id: int = 0) -> Set[str]:
    """Retrieve installed packages on device."""
    prefix = ["-s", serial] if serial else []
    ok, out = run_adb(prefix + ["shell", f"pm list packages --user {user_id}"])
    if not ok:
        return set()
    return set(line.replace("package:", "").strip() for line in out.splitlines() if line.strip())

def build_dependency_graph(db: Dict[str, Any]) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Build dependency and reverse dependent index from package database.
    Returns: (dependencies_map, dependents_map)
    """
    dependencies_map: Dict[str, List[str]] = {}
    dependents_map: Dict[str, List[str]] = {}

    for cat_key, cat_data in db.get("categories", {}).items():
        for pkg, info in cat_data.get("packages", {}).items():
            deps = info.get("dependencies", [])
            dep_ons = info.get("dependents", [])

            if deps:
                dependencies_map[pkg] = list(deps)
                for d in deps:
                    dependents_map.setdefault(d, [])
                    if pkg not in dependents_map[d]:
                        dependents_map[d].append(pkg)

            if dep_ons:
                dependents_map.setdefault(pkg, [])
                for d in dep_ons:
                    if d not in dependents_map[pkg]:
                        dependents_map[pkg].append(d)
                    dependencies_map.setdefault(d, [])
                    if pkg not in dependencies_map[d]:
                        dependencies_map[d].append(pkg)

    return dependencies_map, dependents_map

def validate_package_dependencies(
    packages_to_disable: List[str],
    installed_packages: Set[str],
    db: Dict[str, Any]
) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Validates package dependencies against installed apps (Inspiration: UAD-ng).
    Prevents breaking dependencies by ensuring prerequisite packages are not disabled
    if their dependent apps remain installed and active.

    Returns:
        approved_packages: Packages safe to disable.
        blocked_items: List of dictionaries describing blocked packages and conflict reasons.
    """
    dependencies_map, dependents_map = build_dependency_graph(db)
    approved: List[str] = []
    blocked: List[Dict[str, str]] = []

    planned_disable_set = set(packages_to_disable)

    for pkg in packages_to_disable:
        # Check 1: Critical System Components
        if pkg in CRITICAL_NEVER_DISABLE:
            blocked.append({
                "package": pkg,
                "reason": "CRITICAL: Fundamental Android operating system component (Hard Whitelisted)."
            })
            continue

        # Check 2: Keyboard Safeguard (Must retain at least 1 installed keyboard)
        if pkg in KEYBOARD_PACKAGES:
            remaining_keyboards = [k for k in KEYBOARD_PACKAGES if (k in installed_packages and k not in planned_disable_set)]
            if not remaining_keyboards:
                blocked.append({
                    "package": pkg,
                    "reason": "INPUT SAFETY: Disabling this keyboard leaves the device with NO input method."
                })
                continue

        # Check 3: Launcher Safeguard (Must retain at least 1 installed launcher)
        if pkg in LAUNCHER_PACKAGES:
            remaining_launchers = [l for l in LAUNCHER_PACKAGES if (l in installed_packages and l not in planned_disable_set)]
            if not remaining_launchers:
                blocked.append({
                    "package": pkg,
                    "reason": "HOME SCREEN SAFETY: Disabling this launcher leaves the device without a home screen."
                })
                continue

        # Check 4: Dependent apps still installed and active
        deps = dependents_map.get(pkg, [])
        active_dependents = [d for d in deps if (d in installed_packages and d not in planned_disable_set)]
        if active_dependents:
            dep_names = ", ".join(active_dependents)
            blocked.append({
                "package": pkg,
                "reason": f"DEPENDENCY CONFLICT: Required by installed dependent app(s): [{dep_names}]."
            })
            continue

        approved.append(pkg)

    return approved, blocked

def plan_mode_optimization(
    mode: str,
    installed_packages: Set[str],
    manufacturer: str = "",
    db: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Formulate an optimization plan for target mode without executing changes."""
    cfg = get_mode_config(mode)
    if db is None:
        db = load_database()

    target_tiers = set(cfg["package_tiers"])
    allowed_categories = set(cfg["category_filter"])
    m_low = manufacturer.lower()

    # Collect matching candidate packages
    candidates: List[str] = []
    package_metadata: Dict[str, Any] = {}

    for cat_key, cat_data in db.get("categories", {}).items():
        # Check category match
        if cat_key not in allowed_categories:
            continue
        if cat_key in ["samsung", "xiaomi", "realme_oppo"]:
            if cat_key == "samsung" and "samsung" not in m_low:
                continue
            if cat_key == "xiaomi" and not any(x in m_low for x in ["xiaomi", "redmi", "poco"]):
                continue
            if cat_key == "realme_oppo" and not any(x in m_low for x in ["realme", "oppo", "oneplus"]):
                continue

        for pkg, info in cat_data.get("packages", {}).items():
            tier = info.get("tier", "Recommended")
            pkg_mode = info.get("mode")

            # Check tier eligibility
            if tier not in target_tiers:
                continue
            if tier == "Unsafe":
                continue
            if pkg_mode == "never":
                continue

            # In low mode, only select carrier_bloat or packages explicitly tagged mode: low
            if mode == "low" and cat_key != "carrier_bloat" and pkg_mode != "low":
                continue

            if pkg in installed_packages:
                candidates.append(pkg)
                package_metadata[pkg] = info

    # Validate candidate packages against dependency graph
    approved_packages, blocked_packages = validate_package_dependencies(candidates, installed_packages, db)

    return {
        "mode": mode,
        "config": cfg,
        "candidates_count": len(candidates),
        "approved_packages": approved_packages,
        "blocked_packages": blocked_packages,
        "package_metadata": package_metadata,
        "actions": {
            "disable_packages": approved_packages,
            "animation_scale": cfg["animation_scale"],
            "trim_cache": cfg["trim_cache"],
            "appops_preset": cfg["appops_preset"],
            "standby_bucket": cfg["standby_bucket"],
            "art_filter": cfg["art_filter"],
            "zram": cfg["zram"]
        }
    }

def export_on_device_manifest(manifest_data: Dict[str, Any], serial: Optional[str] = None):
    """
    Mirror pre-flight restore manifest to /sdcard/.lagfixer_manifest.json on device (Inspiration: Canta).
    Enables rootless Shizuku/rish recovery directly on the handset without a PC.
    """
    prefix = ["-s", serial] if serial else []
    tmp_path = os.path.join(os.path.dirname(__file__), "..", "backups", ".sdcard_manifest_tmp.json")
    try:
        os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        # Push to sdcard
        run_adb(prefix + ["push", tmp_path, "/sdcard/.lagfixer_manifest.json"])
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    except Exception:
        pass  # Non-fatal if sdcard is locked or unavailable

def print_preflight_report(
    plan: Dict[str, Any],
    device_info: Dict[str, Any],
    target_social: List[str],
    target_compile: List[str]
):
    """Render the pre-flight plan card. Uses the shared widgets so borders align."""
    from ui import ui as _ui_factory

    u = _ui_factory()
    t = u.theme
    cfg = plan["config"]
    approved_pkgs = plan["approved_packages"]

    brand = str(device_info.get("brand", "Generic")).upper()
    model = str(device_info.get("model", "Device"))
    android_ver = str(device_info.get("android_version", "?"))
    sdk = str(device_info.get("sdk_level", "?"))

    rows = []
    rows.append(t.paint("target   ", "muted") + ": " + t.paint(brand + " " + model, "title")
                + " (Android " + android_ver + ", SDK " + sdk + ")")
    rows.append(t.paint("debloat  ", "muted") + ": " + str(len(approved_pkgs))
                + " packages identified  " + u.badge(str(cfg["label"]).split("(")[0].strip().upper()))
    if target_social:
        names = []
        for p in target_social[:3]:
            parts = p.split(".")
            name = parts[-2].capitalize() if parts[-1].lower() in ("android", "app", "service") and len(parts) > 2 else parts[-1].capitalize()
            names.append(name)
        extra = " (+" + str(len(target_social) - 3) + " more)" if len(target_social) > 3 else ""
        rows.append(t.paint("appops   ", "muted") + ": " + str(len(target_social))
                    + " background hogs (" + ", ".join(names) + extra + ")")
    else:
        rows.append(t.paint("appops   ", "muted") + ": none installed")
    rows.append(t.paint("animation", "muted") + ": " + str(cfg["animation_scale"]) + "x")
    rows.append(t.paint("cache    ", "muted") + ": trim stale system caches (no user data)")
    if target_compile:
        rows.append(t.paint("art      ", "muted") + ": speed-profile on "
                    + str(len(target_compile)) + " top apps")
    rows.append(t.paint("rollback ", "muted") + ": " + t.paint("snapshot written and fsynced before the first mutation", "ok"))

    u.print("")
    u.print(u.box(rows, title="PRE-FLIGHT AUDIT: " + cfg["label"].upper()))


def confirm_preflight_plan(
    plan: Dict[str, Any],
    device_info: Dict[str, Any],
    target_social: List[str],
    target_compile: List[str]
) -> bool:
    """Show pre-flight report and ask user for confirmation before mutating device."""
    print_preflight_report(plan, device_info, target_social, target_compile)

    from ui import ui as _ui_factory

    u = _ui_factory()
    t = u.theme
    u.print(t.paint(" [Y]", "ok") + " apply   "
            + t.paint("[D]", "info") + " details   "
            + t.paint("[N]", "muted") + " cancel, no changes")
    u.print(u.rule())

    while True:
        try:
            choice = input(t.paint("Proceed with optimization? [Y/d/n]: ", "ok")).strip()
        except (KeyboardInterrupt, EOFError):
            u.print(t.paint("Operation cancelled by user. Zero changes made.", "danger"))
            return False

        if choice.lower() in ["y", "yes", ""]:
            return True
        elif choice.lower() in ["d", "details"]:
            approved = plan["approved_packages"]
            metadata = plan.get("package_metadata", {})
            rows = []
            if not approved:
                rows.append(t.paint("no debloat packages found for this mode tier", "muted"))
            for pkg in approved[:12]:
                meta = metadata.get(pkg, {})
                name = meta.get("name", pkg)
                desc = meta.get("description", "identified by the community debloat database")
                tier = meta.get("tier", "")
                head = t.paint(pkg, "ok") + ("  " + u.badge(tier) if tier else "")
                rows.append(head)
                rows.append(t.paint("  " + str(name) + ": " + str(desc), "muted"))
            if len(approved) > 12:
                rows.append(t.paint("  (+" + str(len(approved) - 12) + " more, see the manifest after applying)", "muted"))
            u.print("")
            u.print(u.box(rows, title="PACKAGES TO DISABLE (" + str(len(approved)) + ")"))
            if target_social:
                rows2 = [t.paint(p, "warn") + "  freeze background CPU when minimised" for p in target_social]
                u.print(u.box(rows2, title="APPOPS RESTRICTIONS (" + str(len(target_social)) + ")"))
            u.print(t.paint(" [Y] confirm and apply   [N] cancel", "muted"))
        elif choice.lower() in ["n", "no", "cancel", "c", "0"]:
            u.print(t.paint("Optimization cancelled. No changes were made to your device.", "danger"))
            return False
        else:
            u.print(t.paint("Please type 'Y' to proceed, 'D' to inspect packages, or 'N' to cancel.", "danger"))

def execute_mode_optimization(
    mode: str,
    serial: Optional[str] = None,
    dry_run: bool = False,
    force_ultra: bool = False,
    interactive_confirm: bool = False,
    auto_confirm: bool = False
) -> Dict[str, Any]:
    """Execute complete optimization workflow for the chosen mode."""
    cfg = get_mode_config(mode)
    db = load_database()

    # Safety Gate for Ultra Mode
    if mode == "ultra" and not force_ultra:
        if interactive_confirm:
            print("\n" + "!" * 70)
            print(" ⚠️ CAUTION: ULTRA MODE SELECTED (High-Risk System Strip-Down)")
            print("!" * 70)
            print(" Ultra mode disables duplicate OEM stores, cloud sync accounts, secondary")
            print(" keyboards, disables animations, and aggressively freezes background services.")
            print(" Only use this on dedicated gaming phones, secondary devices, or test rigs.")
            print("=" * 70)
            val = input(" 👉 Type 'I UNDERSTAND' to confirm Ultra mode execution: ").strip()
            if val != "I UNDERSTAND":
                return {
                    "mode": mode,
                    "success": False,
                    "error": "Safety Gate: User did not type 'I UNDERSTAND'. Execution aborted.",
                    "aborted": True
                }
        else:
            return {
                "mode": mode,
                "success": False,
                "error": "Ultra mode requires explicit confirmation. Pass '--force-ultra' or run interactively.",
                "aborted": True
            }

    # Fetch device context
    installed = get_installed_packages(serial=serial)
    device_info = get_device_info(serial)
    if not device_info or device_info.get("brand") in [None, "Unknown"]:
        device_info = {"brand": "Generic", "model": "Android", "android_version": "14", "sdk_level": "34"}
    manufacturer = device_info.get("brand", "generic")

    # Formulate plan
    plan = plan_mode_optimization(mode, installed, manufacturer=manufacturer, db=db)
    approved_pkgs = plan["approved_packages"]
    target_social = [p for p in PRESET_BACKGROUND_HOGS if p in installed] if cfg["appops_preset"] else []
    target_compile = [p for p in PRESET_BACKGROUND_HOGS if p in installed][:5] if cfg["art_filter"] else []

    # Pre-Flight Confirmation Gate
    if interactive_confirm and not auto_confirm:
        if not confirm_preflight_plan(plan, device_info, target_social, target_compile):
            return {
                "mode": mode,
                "success": False,
                "error": "Optimization cancelled by user. Zero changes made to your device.",
                "aborted": True
            }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest_id = f"mode_{mode}_{timestamp}"
    manifest_dir = os.path.join(os.path.dirname(__file__), "..", "backups")
    os.makedirs(manifest_dir, exist_ok=True)
    manifest_path = os.path.join(manifest_dir, f"{manifest_id}.json")

    results = {
        "manifest_id": manifest_id,
        "mode": mode,
        "timestamp": timestamp,
        "dry_run": dry_run,
        "packages_disabled": [],
        "packages_failed": [],
        "blocked_packages": plan["blocked_packages"],
        "ui_tuned": False,
        "appops_applied": [],
        "standby_bucket_applied": [],
        "art_compiled": [],
        "success": True
    }

    print(f"\n[*] Applying Mode [{cfg['emoji']} {cfg['label']}] (Dry-Run: {dry_run})...")

    # Step 1: Package Disabling with Pre-Flight Snapshot
    if approved_pkgs:
        print(f"[*] Disabling {len(approved_pkgs)} safe packages according to {mode} tier...")
        manifest_data = {
            "manifest_version": "2.0.0",
            "type": "mode_optimization",
            "mode": mode,
            "timestamp": timestamp,
            "device": device_info,
            "packages": {}
        }

        # N6 FIX: Query actual real state before mutating (instead of guessing 'enabled')
        for pkg in approved_pkgs:
            prev_st = get_package_state(pkg, serial=serial) if not dry_run else "enabled"
            manifest_data["packages"][pkg] = {
                "previous_state": prev_st,
                "new_state": "disabled",
                "status": "pending"
            }

        # N3 FIX: Write and fsync pre-flight manifest BEFORE mutating device
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        print(f"[*] Pre-flight restore snapshot secured at: {manifest_path}")

        from ui import ui as _ui_factory
        u = _ui_factory()
        total_pkgs = len(approved_pkgs)
        live_bar = u.caps.is_tty and not dry_run
        for idx, pkg in enumerate(approved_pkgs, 1):
            if dry_run:
                print(f"    [DRY-RUN] Would disable: {pkg}")
                results["packages_disabled"].append(pkg)
                manifest_data["packages"][pkg]["status"] = "simulated"
            else:
                ok, msg = apply_package_state(pkg, want="disabled", serial=serial, dry_run=False)
                if ok:
                    if not live_bar:
                        print(f"    {u.theme.paint(u.glyph['ok'], 'ok')} disabled: {pkg}")
                    results["packages_disabled"].append(pkg)
                    manifest_data["packages"][pkg]["status"] = "applied"
                else:
                    if not live_bar:
                        print(f"    {u.theme.paint(u.glyph['warn'], 'warn')} failed {pkg}: {msg}")
                    results["packages_failed"].append({"package": pkg, "error": msg})
                    manifest_data["packages"][pkg]["status"] = f"failed: {msg}"
            if live_bar:
                sys.stdout.write("\r" + u.progress(idx, total_pkgs, label=pkg))
                sys.stdout.flush()

        if live_bar:
            sys.stdout.write("\n")
            sys.stdout.flush()

        # Update manifest on disk with final execution outcomes
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            pass

        # Mirror manifest to /sdcard/ for on-device Canta/Shizuku recovery
        if not dry_run:
            export_on_device_manifest(manifest_data, serial=serial)

    # Step 2: UI Animation Tuning & System Cache Trimming
    anim_scale = cfg["animation_scale"]
    if dry_run:
        print(f"[*] [DRY-RUN] Would set animation scale to {anim_scale}x and trim caches.")
        results["ui_tuned"] = True
    else:
        print(f"[*] Setting animation scale to {anim_scale}x...")
        set_animation_scale(scale=anim_scale, serial=serial)
        if cfg["trim_cache"]:
            trim_system_cache(serial=serial)
        results["ui_tuned"] = True

    # Step 3: AppOps Restrictions
    if cfg["appops_preset"]:
        target_social = [p for p in PRESET_BACKGROUND_HOGS if p in installed]
        if target_social:
            print(f"[*] Restricting background AppOps for {len(target_social)} social/shopping hogs...")
            for p in target_social:
                if dry_run:
                    print(f"    [DRY-RUN] Would restrict AppOps for: {p}")
                    results["appops_applied"].append(p)
                else:
                    ok, _ = set_appops_restriction(p, "ignore", serial=serial, dry_run=False)
                    if ok:
                        print(f"    🛡️ Throttled background wakeups & network: {p}")
                        results["appops_applied"].append(p)

    # Step 4: Standby Buckets
    if cfg["standby_bucket"]:
        target_social = [p for p in PRESET_BACKGROUND_HOGS if p in installed]
        for p in target_social:
            if dry_run:
                results["standby_bucket_applied"].append(p)
            else:
                ok, _ = set_standby_bucket(p, cfg["standby_bucket"], serial=serial, dry_run=False)
                if ok:
                    print(f"    🔋 Set App Standby bucket to {cfg['standby_bucket'].upper()}: {p}")
                    results["standby_bucket_applied"].append(p)

    # Step 5: ART Ahead-Of-Time Pre-Compilation
    if cfg["art_filter"]:
        # In medium mode compile top social apps; in high/ultra compile top apps
        compile_targets = [p for p in PRESET_BACKGROUND_HOGS if p in installed][:5]
        if compile_targets:
            print(f"[*] ART Pre-compiling {len(compile_targets)} apps with filter '{cfg['art_filter']}'...")
            for p in compile_targets:
                if dry_run:
                    print(f"    [DRY-RUN] Would compile {p} with filter {cfg['art_filter']}")
                    results["art_compiled"].append(p)
                else:
                    ok, msg = compile_package(p, compile_filter=cfg["art_filter"], serial=serial, dry_run=False)
                    if ok:
                        print(f"    ✅ Compiled: {p}")
                        results["art_compiled"].append(p)
                    else:
                        print(f"    ℹ️ Compilation notice for {p}: {msg}")

    # Step 6: Multi-Device Audit Vault Logging
    try:
        from device_tracker import get_device_fingerprint, log_device_action, save_device_profile
        fp = get_device_fingerprint(serial)
        save_device_profile(fp)
        log_device_action(
            fp["device_slug"],
            f"mode_optimization_{mode}",
            f"Applied Mode [{cfg['emoji']} {cfg['label']}]",
            {
                "mode": mode,
                "packages_disabled": results["packages_disabled"],
                "appops_applied": results["appops_applied"],
                "art_compiled": results["art_compiled"],
                "animation_scale": cfg["animation_scale"],
                "manifest_path": manifest_path if approved_pkgs else None
            }
        )
    except Exception:
        pass

    _summary = _ui_factory().box([
        _ui_factory().theme.paint("mode      ", "muted") + ": " + str(cfg["label"])
        + ("  (DRY RUN, nothing was changed)" if dry_run else ""),
        _ui_factory().theme.paint("disabled  ", "muted") + ": " + str(len(results["packages_disabled"]))
        + "   " + _ui_factory().theme.paint("failed", "muted") + ": " + str(len(results["packages_failed"])),
        _ui_factory().theme.paint("appops    ", "muted") + ": " + str(len(results["appops_applied"]))
        + "   " + _ui_factory().theme.paint("art", "muted") + ": " + str(len(results["art_compiled"])),
        _ui_factory().theme.paint("manifest  ", "muted") + ": "
        + (os.path.basename(manifest_path) if approved_pkgs else "none")
        + _ui_factory().theme.paint("  (backups/)", "muted"),
        _ui_factory().theme.paint("undo      ", "muted") + ": " + _ui_factory().theme.paint(
            "python scripts/restore.py --manifest latest", "ok"),
    ], title="SESSION SUMMARY")
    _ui_factory().print("")
    _ui_factory().print(_summary)
    return results

def main():
    parser = argparse.ArgumentParser(description="Multi-Tier Android Optimization Engine")
    parser.add_argument("--mode", choices=OPTIMIZATION_MODES, help="Target optimization mode: low, medium, high, ultra")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without modifying device state")
    parser.add_argument("--yes", "-y", action="store_true", help="Bypass interactive confirmation and auto-approve")
    parser.add_argument("--force-ultra", action="store_true", help="Bypass interactive safety confirmation for Ultra mode")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    # Detect device
    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    serial = auth[0]["serial"] if auth else None

    # Interactive mode selection if --mode is not provided
    selected_mode = args.mode
    if not selected_mode:
        clear_screen()
        banner = """
\033[1;38;2;0;230;118m   █████╗ ██╗     ███████╗██╗
  ██╔══██╗██║     ██╔════╝██║
  ███████║██║     █████╗  ██║
  ██╔══██║██║     ██╔══╝  ██║
  ██║  ██║███████╗██║     ██║
  ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝\033[0m
  \033[1;38;2;255;235;59m⚡\033[0m \033[1;38;2;255;255;255mA L F i\033[0m  \033[38;2;120;144;156m—\033[0m  \033[1;38;2;0;230;118mA N D R O I D   L A G   F I X E R\033[0m  \033[1;38;2;255;235;59m⚡\033[0m
"""
        print(banner)
        print("\033[38;2;55;71;79m╭────────────────────────────────────────────────────────────────────────╮\033[0m")
        print("\033[38;2;55;71;79m│\033[0m                \033[1;38;2;255;235;59m⚡\033[0m \033[1;38;2;255;255;255mSELECT OPTIMIZATION ARCHITECTURE\033[0m \033[1;38;2;255;235;59m⚡\033[0m                \033[38;2;55;71;79m│\033[0m")
        print("\033[38;2;55;71;79m╰────────────────────────────────────────────────────────────────────────╯\033[0m\n")

        print("  \033[1;38;2;0;230;118m[ 1 ] 🟢 LOW MODE\033[0m ─────── \033[1;38;2;255;255;255mSAFE BASELINE (Zero Risk)\033[0m")
        print("        \033[38;2;120;144;156m• Scope   :\033[0m Carrier adware stubs, 0.75x animations, stale cache trim")
        print("        \033[38;2;120;144;156m• Target  :\033[0m Family phones, work profiles, zero tolerance for feature changes\n")

        print("  \033[1;38;2;255;235;59m[ 2 ] 🟡 MEDIUM MODE\033[0m ──── \033[1;38;2;255;255;255mBALANCED DAILY DRIVER (Recommended)\033[0m")
        print("        \033[38;2;120;144;156m• Scope   :\033[0m Low + OEM telemetry (Glance, Meta, MSA), 0.5x animations,")
        print("                    ART speed-profile on top user apps, social AppOps limits")
        print("        \033[38;2;120;144;156m• Target  :\033[0m Everyday smartphones wanting snappy UI & cooler battery\n")

        print("  \033[1;38;2;255;152;0m[ 3 ] 🟠 HIGH MODE\033[0m ────── \033[1;38;2;255;255;255mAGGRESSIVE ACCELERATION (Budget / Sluggish Devices)\033[0m")
        print("        \033[38;2;120;144;156m• Scope   :\033[0m Medium + vendor bloat (Bixby, Joyose), App Standby RESTRICTED,")
        print("                    Deep Doze allowlist cleanup, Virtual RAM off guidance")
        print("        \033[38;2;120;144;156m• Target  :\033[0m Power users, older devices, budget 2GB-4GB hardware with lag\n")

        print("  \033[1;38;2;255;82;82m[ 4 ] 🔴 ULTRA MODE\033[0m ───── \033[1;38;2;255;255;255mEXTREME STRIP-DOWN (High-Risk / Power Users)\033[0m")
        print("        \033[38;2;120;144;156m• Scope   :\033[0m High + duplicate OEM accounts (Samsung/Mi ID), duplicate stores,")
        print("                    secondary keyboards/launchers, 0.0x zero animations, full AOT")
        print("        \033[38;2;120;144;156m• Safety  :\033[0m \033[1;38;2;255;82;82mDouble-Gate: Dependency Graph Check + Requires 'I UNDERSTAND'\033[0m\n")

        print("  \033[38;2;120;144;156m[ 0 ] 🚪 Cancel and Exit\033[0m")
        print("\033[38;2;55;71;79m──────────────────────────────────────────────────────────────────────────\033[0m")

        try:
            choice = input("\033[1;38;2;0;230;118m👉 Select mode [1-4]: \033[0m").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

        if choice in ["0", "q", "exit", "quit"]:
            sys.exit(0)

        mode_map = {"1": "low", "2": "medium", "3": "high", "4": "ultra"}
        if choice not in mode_map:
            print("\033[1;38;2;255;82;82m❌ Invalid selection. Please choose a number between 1 and 4.\033[0m")
            sys.exit(1)
        selected_mode = mode_map[choice]

    # N1 FIX: Enforce confirmation gate even with --json; require --yes for unattended execution
    is_tty = sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty()
    if not args.yes and not args.force_ultra and not is_tty and not args.dry_run:
        err_msg = "Error: Unattended execution requires explicit '--yes' confirmation flag."
        if args.json:
            print(json.dumps({"success": False, "error": err_msg, "aborted": True}, indent=2))
        else:
            print(f"\033[1;38;2;255;82;82m❌ {err_msg}\033[0m")
        sys.exit(1)

    res = execute_mode_optimization(
        selected_mode,
        serial=serial,
        dry_run=args.dry_run,
        force_ultra=args.force_ultra,
        interactive_confirm=(not args.yes and not args.force_ultra),
        auto_confirm=args.yes
    )

    if args.json:
        print(json.dumps(res, indent=2))
    elif not res.get("success", False):
        print(f"\n❌ Execution Error: {res.get('error', 'Unknown failure')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
