#!/usr/bin/env python3
"""
scripts/update_database.py - Community Package Database Sync & Schema Validator

Merges upstream community-verified debloat classifications (from UAD-ng or local offline fixtures)
into package_database.json with strict package name regex validation, OEM categorisation,
and automated pre-flight database backups.
"""

import sys
import os
import json
import urllib.request
import urllib.error
import argparse
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from connect import validate_package_name

UPSTREAM_UAD_URL = (
    "https://raw.githubusercontent.com/Universal-Debloater-Alliance/"
    "universal-android-debloater-next-generation/main/resources/assets/uad_lists.json"
)

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

DB_PATH = get_database_path()

def categorize_package(pkg: str) -> str:
    """Categorize an Android package name into an OEM or ecosystem group."""
    p = pkg.lower()
    if p.startswith("com.samsung.") or p.startswith("com.sec.") or p.startswith("com.osp."):
        return "samsung"
    if p.startswith("com.miui.") or p.startswith("com.xiaomi.") or p.startswith("com.mi."):
        return "xiaomi"
    if p.startswith("com.oplus.") or p.startswith("com.heytap.") or p.startswith("com.coloros.") or p.startswith("com.nearme."):
        return "realme"
    if p.startswith("com.google.") or p.startswith("com.android."):
        return "google"
    return "general_bloat"

def backup_database() -> str:
    """Create timestamped pre-flight backup snapshot of package_database.json."""
    if not os.path.exists(DB_PATH):
        return ""
    manifest_dir = os.path.join(os.path.dirname(__file__), "..", "backups")
    os.makedirs(manifest_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(manifest_dir, f"package_database_backup_{timestamp}.json")
    with open(DB_PATH, "r", encoding="utf-8") as f_in:
        content = f_in.read()
    with open(backup_file, "w", encoding="utf-8") as f_out:
        f_out.write(content)
    return backup_file

def load_local_database() -> Dict[str, Any]:
    """Load existing package database."""
    if not os.path.exists(DB_PATH):
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "version": "1.0.0",
            "description": "Multi-OEM Android bloatware, telemetry, and security risk database",
            "categories": {}
        }
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_community_list(raw_data: Any) -> Tuple[Dict[str, Dict[str, Any]], int, int]:
    """
    Parse UAD-ng list format into structured packages categorized by OEM.
    Supports both dictionary mapping format (current upstream UAD-ng) and list format.
    Returns (categorized_dict, accepted_count, rejected_count).
    """
    categorized: Dict[str, Dict[str, Any]] = {}
    accepted = 0
    rejected = 0

    if not raw_data:
        return categorized, accepted, rejected

    # Format 1: Dictionary mapping { "com.example.app": { "removal": "Recommended", ... } }
    if isinstance(raw_data, dict):
        items_to_process = []
        for pkg_id, meta in raw_data.items():
            if isinstance(meta, dict):
                item_dict = dict(meta)
                item_dict.setdefault("id", pkg_id)
                items_to_process.append(item_dict)
            elif isinstance(meta, str):
                items_to_process.append({"id": pkg_id, "list": meta})
    elif isinstance(raw_data, list):
        items_to_process = raw_data
    else:
        return categorized, accepted, rejected

    for item in items_to_process:
        if not isinstance(item, dict):
            if isinstance(item, str) and validate_package_name(item.strip()):
                pkg = item.strip()
                tier = "Advanced"
                description = "Identified by community debloat database."
                dependencies = []
                dependents = []
            else:
                rejected += 1
                continue
        else:
            pkg = item.get("id", "").strip()
            if not validate_package_name(pkg):
                rejected += 1
                continue

            raw_tier = item.get("removal") or item.get("list") or "Advanced"
            raw_tier_str = str(raw_tier).capitalize()
            tier = raw_tier_str if raw_tier_str in ["Recommended", "Advanced", "Expert", "Unsafe"] else "Advanced"
            description = (item.get("description") or "").strip() or "Identified by community debloat database."
            dependencies = item.get("dependencies") or []
            dependents = item.get("neededBy") or []

        category = categorize_package(pkg)
        if category not in categorized:
            categorized[category] = {}

        pkg_entry: Dict[str, Any] = {
            "name": pkg.split(".")[-1].replace("_", " ").title(),
            "tier": tier,
            "impact": description
        }
        if dependencies:
            pkg_entry["dependencies"] = dependencies
        if dependents:
            pkg_entry["dependents"] = dependents

        categorized[category][pkg] = pkg_entry
        accepted += 1

    return categorized, accepted, rejected

def merge_databases(
    existing: Dict[str, Any],
    incoming: Dict[str, Dict[str, Any]]
) -> Tuple[Dict[str, Any], int, int]:
    """
    Merge incoming community packages into existing database while preserving custom local edits.
    Returns (updated_db, new_packages_count, updated_packages_count).
    """
    new_count = 0
    updated_count = 0
    categories = existing.setdefault("categories", {})

    for cat_name, pkgs in incoming.items():
        if cat_name not in categories:
            categories[cat_name] = {
                "name": cat_name.replace("_", " ").title(),
                "packages": {}
            }
        cat_pkgs = categories[cat_name].setdefault("packages", {})

        for pkg, meta in pkgs.items():
            if pkg not in cat_pkgs:
                cat_pkgs[pkg] = meta
                new_count += 1
            else:
                # Keep local curated classifications and modes intact
                if "mode" in cat_pkgs[pkg]:
                    # Merge extra dependencies/dependents without overwriting curated tier
                    if meta.get("dependencies") and not cat_pkgs[pkg].get("dependencies"):
                        cat_pkgs[pkg]["dependencies"] = meta["dependencies"]
                    if meta.get("dependents") and not cat_pkgs[pkg].get("dependents"):
                        cat_pkgs[pkg]["dependents"] = meta["dependents"]
                else:
                    if meta.get("tier") and cat_pkgs[pkg].get("tier") != meta["tier"]:
                        cat_pkgs[pkg]["tier"] = meta["tier"]
                        updated_count += 1

    existing["last_updated"] = datetime.now().isoformat()
    return existing, new_count, updated_count

def fetch_upstream_data(source_url: str = UPSTREAM_UAD_URL, timeout: int = 10) -> Optional[List[Dict[str, Any]]]:
    """Download upstream community list from URL."""
    try:
        req = urllib.request.Request(source_url, headers={"User-Agent": "android-lag-fixer/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content)
    except Exception as e:
        return None

def main():
    parser = argparse.ArgumentParser(description="Community Package Database Sync & Schema Validator")
    parser.add_argument("--url", default=UPSTREAM_UAD_URL, help="Upstream URL for UAD-ng package list")
    parser.add_argument("--file", help="Local JSON file path containing package list (for offline sync)")
    parser.add_argument("--restore-backup", help="Restore package_database.json from a backup file")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying package_database.json")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    # 1. Restore from backup
    if args.restore_backup:
        backup_path = args.restore_backup
        if not os.path.exists(backup_path):
            backup_path = os.path.join(os.path.dirname(__file__), "..", "backups", args.restore_backup)
        if not os.path.exists(backup_path):
            print(f"❌ Backup file not found: {args.restore_backup}")
            sys.exit(1)

        with open(backup_path, "r", encoding="utf-8") as f_in:
            data = f_in.read()
        with open(DB_PATH, "w", encoding="utf-8") as f_out:
            f_out.write(data)

        if args.json:
            print(json.dumps({"status": "restored", "backup": backup_path}, indent=2))
        else:
            print(f"✅ package_database.json successfully restored from {backup_path}")
        return

    # 2. Acquire raw list
    raw_list = None
    if args.file:
        if not os.path.exists(args.file):
            print(f"❌ Input file not found: {args.file}")
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as f:
            raw_list = json.load(f)
    else:
        if not args.json:
            print(f"[*] Fetching community package definitions from upstream...")
        raw_list = fetch_upstream_data(args.url)

    if not raw_list:
        print("⚠️ Could not fetch upstream package database (network unavailable or timeout).")
        print("💡 Use '--file <path>' to import a local JSON list, or try again later.")
        sys.exit(1)

    # 3. Parse and validate
    categorized, accepted, rejected = parse_community_list(raw_list)

    # 4. Backup current database
    backup_file = ""
    if not args.dry_run:
        backup_file = backup_database()

    # 5. Merge
    current_db = load_local_database()
    updated_db, new_count, mod_count = merge_databases(current_db, categorized)

    if not args.dry_run:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(updated_db, f, indent=2)

    total_packages = sum(len(c.get("packages", {})) for c in updated_db.get("categories", {}).values())

    if args.json:
        print(json.dumps({
            "status": "success",
            "dry_run": args.dry_run,
            "backup_manifest": backup_file,
            "new_packages": new_count,
            "updated_packages": mod_count,
            "rejected_malformed": rejected,
            "total_packages": total_packages
        }, indent=2))
        return

    print("\n" + "="*70)
    mode_lbl = "[DRY-RUN] " if args.dry_run else ""
    print(f" 🌐 {mode_lbl}COMMUNITY PACKAGE DATABASE UPDATE COMPLETE")
    print("="*70)
    print(f"  • New Packages Added   : {new_count}")
    print(f"  • Classifications Updated: {mod_count}")
    print(f"  • Malformed / Rejected : {rejected}")
    print(f"  • Total Database Size  : {total_packages} packages")
    if backup_file:
        print(f"  • Pre-Update Backup    : backups/{os.path.basename(backup_file)}")
        print(f"  • Rollback Command     : python scripts/update_database.py --restore-backup {os.path.basename(backup_file)}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
