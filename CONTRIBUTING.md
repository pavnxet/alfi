# Contributing to Android Lag Fixer

We welcome community contributions to make Android devices cleaner, faster, more responsive, and secure!

---

## How You Can Contribute

### 1. Device Reports & Fixture Submissions
To help expand our automated test suite across all OEMs without needing a physical phone farm:
- Submit sanitized `dumpsys` outputs to `tests/fixtures/` (e.g. `tests/fixtures/<oem>_<model>_dumpsys.txt`).
- Share device specifications:
  - Model: `adb shell getprop ro.product.model`
  - Android OS / SDK: `adb shell getprop ro.build.version.sdk`
  - OEM Skin: (One UI, HyperOS, ColorOS, OxygenOS, Pixel Experience)

### 2. Package Database & Classification Updates
- Suggest new bloatware, telemetry, or adware definitions in `package_database.json`.
- Adhere strictly to the four-tier taxonomy:
  - `Recommended`: 100% safe to disable for all users (adware stubs, diagnostic telemetry).
  - `Advanced`: Safe to disable unless the user relies on that specific vendor ecosystem.
  - `Expert`: Power user customizations only.
  - `Unsafe`: Essential subsystems (SystemUI, Telephony, Keyguard, WebView, OTA). **Never touch.**

### 3. Benchmarking & Empirical Proof
- Share before-and-after benchmark runs from `python scripts/bench.py --compare before.json after.json`. Real frame pacing numbers keep our documentation empirical and trustworthy.

---

## Development & Test Guidelines

All contributions must follow our zero-external-dependency rule:

1. **Run Full Test Suite**:
   ```bash
   python -m unittest discover tests -v
   ```
   All 49 unit and integration tests must pass with 100% success rate on Python 3.10 through 3.14.

2. **Syntax Compilation Check**:
   ```bash
   python -m compileall scripts/
   ```

3. **Safe Mutating Commands**:
   - Every script modifying device state must support `--dry-run` and `--json`.
   - All package names must be validated against `validate_package_name(pkg)` to prevent shell injection.
   - Every mutation must automatically generate a pre-flight rollback manifest in `backups/`.
   - Never log personal identifiers, phone numbers, or hardware serial numbers in public commits.
