#!/usr/bin/env python3
"""
scripts/export_shizuku.py - On-Device Shizuku & Rish Optimization Script Exporter

Exports self-contained shell scripts that can be executed directly on Android phones
without a PC using Termux and Shizuku's `rish` shell.
Always generates:
1. An optimization script (apply_optimization_<profile>.sh)
2. A matched 1-click rollback script (rollback_optimization_<profile>.sh)
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import List, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from appops_restrict import PRESET_BACKGROUND_HOGS

DEFAULT_OEM_BLOAT = {
    "samsung": [
        "com.aura.oobe.samsung",
        "com.samsung.android.airtel.stubapp",
        "com.samsung.android.diagmonagent",
        "com.samsung.android.securitylogagent",
        "com.samsung.android.rubin.app",
        "com.samsung.android.dqagent",
        "com.samsung.android.da.daagent",
        "com.sec.android.app.billing",
        "com.samsung.android.game.gamehome",
        "com.samsung.android.allshare.service.mediashare",
        "com.samsung.android.allshare.service.fileshare"
    ],
    "xiaomi": [
        "com.miui.analytics",
        "com.miui.analytics.go",
        "com.miui.cleaner",
        "com.miui.cleaner.go",
        "com.miui.android.fashiongallery",
        "com.miui.msa.global",
        "com.xiaomi.mipicks",
        "com.mi.globalbrowser"
    ],
    "realme": [
        "com.heytap.mcs",
        "com.oplus.statistics.rom",
        "com.oplus.onetrace",
        "com.heytap.pictorial",
        "com.nearme.gamecenter"
    ],
    "google": [
        "com.google.android.youtube",
        "com.google.android.apps.tachyon",
        "com.google.android.videos"
    ]
}

def generate_shizuku_scripts(
    profile: str,
    output_dir: str,
    packages_to_disable: List[str],
    packages_to_restrict: List[str]
) -> Tuple[str, str]:
    """Generate both optimization script and rollback script for Shizuku/rish."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    opt_filename = f"apply_optimization_{profile}_{timestamp}.sh"
    rb_filename = f"rollback_optimization_{profile}_{timestamp}.sh"
    opt_path = os.path.join(output_dir, opt_filename)
    rb_path = os.path.join(output_dir, rb_filename)

    # 1. Build Optimization Script
    opt_lines = [
        "#!/bin/sh",
        "# ==================================================================",
        f"# Android Lag Fixer - Shizuku / Rish Optimization Script ({profile})",
        f"# Project: ALFi - https://github.com/pavnxet/alfi",
        f"# Author: Pavneet Singh (@pavnxet)",
        f"# Generated: {datetime.now().isoformat()}",
        "# Usage via Termux & Shizuku: rish " + opt_filename,
        "# ==================================================================",
        "",
        "LOGFILE=\"/sdcard/lagfixer_shizuku.log\"",
        "echo \"=== Starting Optimization: $(date) ===\" >> \"$LOGFILE\"",
        "",
        "# Step 1: Disable Safe OEM Bloatware",
    ]
    for p in packages_to_disable:
        opt_lines.append(f"echo \"[*] Disabling: {p}\"")
        opt_lines.append(f"pm disable-user --user 0 {p} >> \"$LOGFILE\" 2>&1")
        opt_lines.append(f"am force-stop {p} >> \"$LOGFILE\" 2>&1")

    opt_lines.extend([
        "",
        "# Step 2: Apply AppOps Limits & Standby Buckets to Background Hogs",
    ])
    for p in packages_to_restrict:
        opt_lines.append(f"echo \"[*] Restricting: {p}\"")
        opt_lines.append(f"cmd appops set {p} RUN_IN_BACKGROUND ignore >> \"$LOGFILE\" 2>&1")
        opt_lines.append(f"cmd appops set {p} RUN_ANY_IN_BACKGROUND ignore >> \"$LOGFILE\" 2>&1")
        opt_lines.append(f"am set-standby-bucket {p} restricted >> \"$LOGFILE\" 2>&1")

    opt_lines.extend([
        "",
        "# Step 3: Animation Scaling & System Cache Trim",
        "settings put global window_animation_scale 0.5",
        "settings put global transition_animation_scale 0.5",
        "settings put global animator_duration_scale 0.5",
        "pm trim-caches 999999999 >> \"$LOGFILE\" 2>&1",
        "",
        "echo \"=== Optimization Complete: $(date) ===\" >> \"$LOGFILE\"",
        f"echo \"✅ Optimization applied! To revert, run: rish {rb_filename}\"",
        ""
    ])

    # 2. Build Rollback Script
    rb_lines = [
        "#!/bin/sh",
        "# ==================================================================",
        f"# Android Lag Fixer - Shizuku / Rish Rollback Script ({profile})",
        f"# Project: ALFi - https://github.com/pavnxet/alfi",
        f"# Author: Pavneet Singh (@pavnxet)",
        f"# Generated: {datetime.now().isoformat()}",
        "# Usage via Termux & Shizuku: rish " + rb_filename,
        "# ==================================================================",
        "",
        "LOGFILE=\"/sdcard/lagfixer_shizuku.log\"",
        "echo \"=== Starting Rollback: $(date) ===\" >> \"$LOGFILE\"",
        "",
        "# Step 1: Re-enable Disabled Bloatware",
    ]
    for p in packages_to_disable:
        rb_lines.append(f"echo \"[*] Re-enabling: {p}\"")
        rb_lines.append(f"pm enable --user 0 {p} >> \"$LOGFILE\" 2>&1")
        rb_lines.append(f"cmd package install-existing --user 0 {p} >> \"$LOGFILE\" 2>&1")

    rb_lines.extend([
        "",
        "# Step 2: Restore AppOps & Standby Buckets",
    ])
    for p in packages_to_restrict:
        rb_lines.append(f"echo \"[*] Restoring permissions: {p}\"")
        rb_lines.append(f"cmd appops set {p} RUN_IN_BACKGROUND allow >> \"$LOGFILE\" 2>&1")
        rb_lines.append(f"cmd appops set {p} RUN_ANY_IN_BACKGROUND allow >> \"$LOGFILE\" 2>&1")
        rb_lines.append(f"am set-standby-bucket {p} active >> \"$LOGFILE\" 2>&1")

    rb_lines.extend([
        "",
        "# Step 3: Restore Default Animation Scales",
        "settings put global window_animation_scale 1.0",
        "settings put global transition_animation_scale 1.0",
        "settings put global animator_duration_scale 1.0",
        "",
        "echo \"=== Rollback Complete: $(date) ===\" >> \"$LOGFILE\"",
        "echo \"✅ Rollback complete! All packages and permissions restored.\"",
        ""
    ])

    with open(opt_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(opt_lines))

    with open(rb_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(rb_lines))

    return opt_path, rb_path

def main():
    parser = argparse.ArgumentParser(description="Export On-Device Shizuku/Rish Shell Scripts with Paired Rollback")
    parser.add_argument("--profile", default="all", choices=["samsung", "xiaomi", "realme", "google", "social", "all"], help="OEM profile to export")
    parser.add_argument("--output-dir", default=os.path.join(os.path.dirname(__file__), "..", "shizuku_scripts"), help="Output directory for generated shell scripts")
    parser.add_argument("--dry-run", action="store_true", help="Preview generated script paths without writing files")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    # Determine packages
    to_disable = []
    if args.profile == "all":
        for pkgs in DEFAULT_OEM_BLOAT.values():
            to_disable.extend(pkgs)
    elif args.profile in DEFAULT_OEM_BLOAT:
        to_disable = DEFAULT_OEM_BLOAT[args.profile]

    to_restrict = PRESET_BACKGROUND_HOGS if args.profile in ["all", "social"] else []

    if args.dry_run:
        data = {
            "profile": args.profile,
            "dry_run": True,
            "packages_to_disable": len(to_disable),
            "packages_to_restrict": len(to_restrict),
            "output_dir": args.output_dir
        }
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print("\n" + "="*70)
            print(f" 📱 [DRY-RUN] SHIZUKU / RISH SCRIPT EXPORTER: {args.profile.upper()}")
            print("="*70)
            print(f"  • Disable packages : {len(to_disable)}")
            print(f"  • Restrict packages: {len(to_restrict)}")
            print(f"  • Target directory : {args.output_dir}")
            print("="*70 + "\n")
        return

    opt_path, rb_path = generate_shizuku_scripts(
        profile=args.profile,
        output_dir=args.output_dir,
        packages_to_disable=to_disable,
        packages_to_restrict=to_restrict
    )

    if args.json:
        print(json.dumps({
            "status": "success",
            "profile": args.profile,
            "optimization_script": opt_path,
            "rollback_script": rb_path,
            "disabled_count": len(to_disable),
            "restricted_count": len(to_restrict)
        }, indent=2))
        return

    print("\n" + "="*70)
    print(f" 📱 ON-DEVICE SHIZUKU SCRIPTS EXPORTED: {args.profile.upper()}")
    print("="*70)
    print(f"  ⚡ Optimization Script : {opt_path}")
    print(f"  🔄 Paired Rollback     : {rb_path}")
    print(f"  📦 Packages Included   : {len(to_disable)} disabled, {len(to_restrict)} restricted")
    print("\n💡 How to run on your phone without a PC:")
    print("  1. Install Shizuku & Termux from F-Droid.")
    print("  2. Start Shizuku via Wireless Debugging on your phone.")
    print("  3. Transfer the .sh scripts to your phone storage.")
    print(f"  4. In Termux, run: rish {os.path.basename(opt_path)}")
    print(f"  5. To revert at any time, run: rish {os.path.basename(rb_path)}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
