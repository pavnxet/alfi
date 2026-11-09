---
name: phone-lag-fixer
description: Diagnose and fix Android phone lagging, stuttering, and overheating issues; detect sketchy apps, malware, and accessibility hijackers safely without risking the host PC; optimize animation scales, eliminate Virtual RAM thrashing, and debloat OEM telemetry safely with 100% reversible restoration. Trigger when a user mentions phone lag, slow Android device, phone heating, battery drain, sketchy apps, mobile virus scan, debloating, or optimizing Samsung, Realme, Xiaomi, OnePlus, or other Android phones.
---

# Phone Lag Fixer & Security Optimizer

A comprehensive diagnostic, security audit, and performance optimization skill for Android devices using standard, non-root ADB protocols.

## Core Capabilities & Safety Guarantees

1. **Host PC Protection**:
   - **Zero Malware Risk to PC**: Never downloads, extracts, or executes Android binaries (`.apk`, `.dex`, `.so`) on the host computer. All diagnostics and remediations execute remotely inside the Android userland via pure text stream ADB commands.
2. **Disaster-Free & OTA-Safe**:
   - Uses `pm disable-user --user 0 <pkg>` instead of destructive system partition deletions.
   - Automatically saves a pre-flight `restore_manifest_<device>_<timestamp>.json` before any modification.
   - 100% reversible in one click via `scripts/restore.py`.
   - Protects critical update engines (`com.oplus.ota`, `com.google.android.configupdater`), Samsung/Realme account logins, banking apps, and Widevine L1.
3. **Deep Diagnostic Engine**:
   - Profiles CPU load average, memory pressure, ZRAM utilization, and kernel I/O wait states (`f2fs_gc` sleep state `D`).
   - Identifies rogue background hogs (Microsoft Link to Windows, McAfee Device Security, MacroDroid accessibility loops).
4. **Security & Sketchy App Auditor**:
   - Detects **Accessibility Service Hijackers** (banking trojans and keyloggers).
   - Detects **Device Administrator Abuse** (apps preventing uninstallation).
   - Detects **Hidden Ghost Apps** (apps running background services without home screen launcher icons).
   - Flags suspicious sideload sources (apps installed from web browsers rather than official app stores).
5. **Instant UI Responsiveness**:
   - Speeds up window, transition, and animator duration scales (`0.5x`).
   - Reclaims storage and memory via system cache trimming.

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

### Phase 2: Performance Diagnostics
Perform a non-invasive performance audit:
```bash
python scripts/diagnose.py
```
- Evaluates CPU load average (1m, 5m, 15m).
- Checks for **Virtual RAM / RAM Expansion** thrashing (a primary cause of 1–2s micro-stutters on Realme, Samsung, and Xiaomi).
- Lists top CPU-burning packages.

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
python scripts/optimize.py --profile auto
```
- Profiles available: `samsung`, `realme` (Oppo/OnePlus/ColorOS), `xiaomi` (MIUI/HyperOS), `google`, `carrier`, or `auto` (auto-detects connected hardware).
- Applies only `Recommended` tier packages by default.
- Generates a timestamped restore manifest.

### Phase 5: UI Snappiness & Cache Tuning
```bash
python scripts/tweak_ui.py --scale 0.5 --trim-cache
```

### Phase 6: Disaster-Free Restoration (Rollback)
If any desired feature or app was disabled:
```bash
# Restore everything from the latest manifest:
python scripts/restore.py --manifest latest

# Or restore a specific package:
python scripts/restore.py --package com.example.app
```
