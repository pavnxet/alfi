---
name: phone-lag-fixer
description: Diagnose and fix Android phone lagging, stuttering, and overheating issues; detect sketchy apps, malware, and accessibility hijackers safely without risking the host PC; benchmark real frame pacing and jank reduction with dumpsys gfxinfo; optimize animation scales, eliminate zRAM compression thrashing, and debloat OEM telemetry safely with verified state restoration. Trigger when a user mentions phone lag, slow Android device, phone heating, battery drain, sketchy apps, mobile virus scan, debloating, or optimizing Samsung, Realme, Xiaomi, OnePlus, or other Android phones.
---

# Phone Lag Fixer & Security Optimizer

A comprehensive diagnostic, security audit, benchmarking, and performance optimization skill for Android devices using standard, non-root ADB protocols.

## Core Capabilities & Safety Guarantees

1. **Host PC Protection**:
   - **Zero Malware Risk to PC**: Never downloads, extracts, or executes Android binaries (`.apk`, `.dex`, `.so`) on the host computer. All diagnostics and remediations execute remotely inside the Android userland via pure text stream ADB commands.
2. **Disaster-Free & Reversible**:
   - Uses `pm disable-user --user 0 <pkg>` (or version-aware Android 17 resolution) instead of destructive system partition deletions.
   - Automatically saves a pre-flight `restore_manifest_<device>_<timestamp>.json` before any modification.
   - 100% reversible in one click via `scripts/restore.py` (disables preserve all user app data).
   - Protects critical update engines (`com.oplus.ota`, `com.google.android.configupdater`), Samsung/Realme account logins, banking apps, and Widevine L1.
3. **Deep Diagnostic Engine & Benchmarking**:
   - Profiles CPU load average, memory pressure, and zRAM utilization.
   - Measures objective frame pacing, Jank Percentage (>19.1ms for 60Hz), P90/P99 latency, and 1% Low FPS via `scripts/bench.py`.
   - Identifies rogue background hogs (Microsoft Link to Windows, McAfee Device Security, MacroDroid accessibility loops).
4. **Security & Sketchy App Auditor**:
   - Detects **Accessibility Service Hijackers** (banking trojans and keyloggers).
   - Detects **Device Administrator Abuse** (apps preventing uninstallation).
   - Detects **Hidden Ghost Apps** (apps running background services without home screen launcher icons).
   - Flags suspicious permission combinations (Overlay + SMS + Background location).
5. **Instant UI Responsiveness**:
   - Speeds up window, transition, and animator duration scales (`0.5x`).
   - Reclaims storage and memory via system cache trimming.
6. **Multi-Device Local Vault**:
   - Uses hardware chip serials (`ro.serialno`) and Android IDs to track each phone uniquely without name collision via `scripts/device_tracker.py`.

---

## Workflow Guide for Agents & Users

### Phase 1: Device Connection Verification
Run the connection guide to ensure ADB communication and device authorization:
```bash
python scripts/connect.py
```
- If the device is **Unauthorized**, wake the phone screen and guide the user to check *"Always allow from this computer"* and tap **OK**.
- If no device is detected, provide the step-by-step Developer Options and USB Debugging instructions in `references/connection_guide.md`.
- Supports **Wireless Debugging** (Android 11+) using `adb pair` and `adb connect`.

### Phase 2: Performance Diagnostics & Baseline Benchmark
Perform a non-invasive performance audit and measure baseline UI frame pacing:
```bash
python scripts/diagnose.py
python scripts/bench.py --app com.android.settings --duration 8 --save before.json
```
- Evaluates CPU load average (1m, 5m, 15m) and zRAM memory pressure.
- Lists top CPU-burning packages.
- Records baseline frame times and jank ratio.

### Phase 3: Security & Sketchy Apps Audit
Audit third-party apps for suspicious behavior and permissions:
```bash
python scripts/security_audit.py
```
- Audits active Accessibility Services (`dumpsys accessibility`).
- Audits Device Administrators (`dumpsys device_policy`).
- Checks for hidden background apps lacking launcher activities.
- Flags suspicious permission combinations (Overlay + SMS + Background location).
- Offers safe quarantine (`pm disable-user --user 0`) or permission revocation.

### Phase 4: Safe OEM Debloating & Optimization
Apply curated OEM profiles with automatic backup:
```bash
# Preview changes safely:
python scripts/optimize.py --profile auto --dry-run

# Apply optimization:
python scripts/optimize.py --profile auto
```
- Profiles available: `samsung`, `realme` (Oppo/OnePlus/ColorOS), `xiaomi` (MIUI/HyperOS), `google`, `carrier`, or `auto` (auto-detects connected hardware).
- Applies only `Recommended` tier packages by default.
- Generates a timestamped restore manifest.
- Supports `--update-db` to merge upstream community lists from UAD-ng.

### Phase 5: UI Snappiness & Cache Tuning
```bash
python scripts/tweak_ui.py --scale 0.5 --trim-cache
```

### Phase 6: ART Ahead-Of-Time (AOT) Compilation & Reset Points
```bash
# Pre-compile apps for faster launches and zero JIT stutter:
python scripts/compile_speed.py --all-user-apps --filter speed-profile

# Rollback compilation via reset point manifest if needed:
python scripts/compile_speed.py --reset-manifest latest
```

### Phase 7: AppOps Background Execution Limits & Standby Buckets
Restricts apps the user must keep (Instagram, Facebook, Truecaller) from burning background CPU and wake locks:
```bash
# Restrict background execution for common hogs:
python scripts/appops_restrict.py --preset social --bucket restricted

# Restrict specific app:
python scripts/appops_restrict.py --app com.instagram.android --mode ignore --bucket restricted

# Revert / Rollback from snapshot manifest:
python scripts/appops_restrict.py --reset-manifest latest
```

### Phase 8: Post-Optimization Verification
```bash
python scripts/bench.py --app com.android.settings --duration 8 --save after.json
python scripts/bench.py --compare before.json after.json
```

### Phase 9: Disaster-Free Restoration (Rollback)
If any desired feature or app was disabled:
```bash
# Restore everything from the latest manifest:
python scripts/restore.py --manifest latest

# Or restore a specific package:
python scripts/restore.py --package com.example.app
```

### Phase 10: Emergency Feature Rescue & On-Device Shizuku Runner
If any device feature is restricted, broken, or misbehaving:
```bash
# Automatically scan & revive critical system packages (SystemUI, Settings, Dialer, WebView, GMS):
python scripts/rescue.py --fix-critical

# Deep multi-layer package rescue (enable, reinstall, AppOps allow, Standby active, ART reset):
python scripts/rescue.py --rescue-package com.google.android.dialer

# Re-enable all disabled packages:
python scripts/rescue.py --restore-all-disabled

# Hardware Safe Mode recovery guide (when stuck in bootloop):
python scripts/rescue.py --guide samsung

# Export standalone on-device Shizuku (rish) optimization & rollback shell scripts:
python scripts/export_shizuku.py --profile all
```
