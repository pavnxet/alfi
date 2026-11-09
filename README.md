# 📱 Android Lag Fixer & Performance Optimizer (Non-Root ADB)

<p align="center">
  <a href="https://github.com/pavnxet/android-lag-fixer/actions/workflows/ci.yml">
    <img src="https://github.com/pavnxet/android-lag-fixer/actions/workflows/ci.yml/badge.svg" alt="CI Status" />
  </a>
  <img src="https://img.shields.io/badge/Platform-Android_9_--_17+-3DDC84?style=flat&logo=android&logoColor=white" alt="Android 9 to 17+" />
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white" alt="Python 3.9+" />
  <img src="https://img.shields.io/badge/Root-No_Root_Required-blue?style=flat" alt="No Root Required" />
  <img src="https://img.shields.io/badge/Safety-Disables_Preserve_Data-success?style=flat" alt="Safe & Reversible" />
  <img src="https://img.shields.io/badge/License-MIT-orange?style=flat" alt="MIT License" />
</p>

<p align="center">
  <strong>The definitive open-source Android lag fixer, safe OEM debloater, zRAM optimizer, and security audit toolkit.</strong><br />
  <em>Diagnose CPU bottlenecks, eliminate zRAM compression thrashing, detect accessibility trojans and ghost adware, prove framerate gains via real benchmark framestats, and boost UI responsiveness via standard ADB text streams.</em>
</p>

---

## ⚡ Why Do Android Phones Lag Over Time?

Most Android speedup guides recommend aggressive factory resets, third-party "cleaner" apps (which are often adware themselves), or risky root modifications that trip Knox, Widevine L1, and banking security.

In reality, Android lag and micro-stutters stem from 4 distinct kernel and userland bottlenecks:

1. **zRAM Compression Overhead Under Memory Pressure**: OEMs (Samsung RAM Plus, Xiaomi Memory Extension, Realme RAM Expansion) expand virtual memory by sizing up in-memory compressed **zRAM**. On mid-range and budget processors with weak CPU clusters (Cortex-A53/A55), forcing more pages into zRAM causes heavy CPU spikes in `kswapd0` during LZ4/ZSTD compression cycles, competing with the UI thread and causing 1–2 second touch stutters.
2. **Aggressive Background Telemetry & Adware**: Hidden OEM daemons (Glance wallpaper carousels, Xiaomi analytics, Meta/Facebook pre-installed app installers, HeyTap MCS) wake the CPU hundreds of times per hour, preventing deep-sleep C-states and causing thermal throttling.
3. **Accessibility Service & Permission Abuse**: Rogue apps, ghost background services, and banking trojans exploit `BIND_ACCESSIBILITY_SERVICE` and overlay privileges (`SYSTEM_ALERT_WINDOW`), intercepting window managers and causing thousands of compositor page faults.
4. **Sluggish Default UI Animation Scales**: Default `1.0x` window, transition, and animator scales add artificial latency to gesture navigation and app launch animations.

**Android Lag Fixer** solves these bottlenecks at the root level using non-destructive, non-root ADB protocols.

---

## 🚀 Key Features & Capabilities

### 🛡️ 1. Absolute Host PC Isolation
* **Zero Binary Execution on Host**: The toolkit **never downloads, mounts, or executes Android binaries (`.apk`, `.dex`, `.so`) on your PC**.
* **Pure ADB Text Stream Auditing**: All scans, permission audits, and telemetry freezes execute remotely inside the Android userland using standard, sandboxed ADB shell commands (`dumpsys`, `pm`, `settings`).

### 🔍 2. Deep Root-Cause Performance Diagnostics
* **True Kernel Run-Queue Profiling**: Measures 1m, 5m, and 15m CPU load averages to identify true thermal and process saturation.
* **Infamous Background Hogs Detection**: Automatically detects notorious CPU loopers (Microsoft Link to Windows looping at >100% CPU, McAfee Device Security, MacroDroid compositor hooks).
* **ZRAM Memory Pressure Analysis**: Inspects physical RAM headroom, active swap compression saturation, and kernel swap daemon activity.

### 🏁 3. Objective Frame Pacing & Jank Benchmark Harness
* **Real-World Framerate & Frame Pacing (`dumpsys gfxinfo framestats`)**: Measures actual frame durations directly from the Android graphics compositor.
* **Empirical Speedup Metrics**: Calculates Jank Percentage (>19.1ms for 60Hz), P50/P90/P99 latency, and 1% Low FPS.
* **Before-vs-After Comparison Table**: Run `--compare before.json after.json` to prove exact latency improvements with hard data.

### 🕵️ 4. Security & Sketchy Apps Auditor
* **Accessibility Service Hijackers**: Audits apps holding screen-reading and click-simulation permissions (primary vector for banking trojans like TeaBot and stalkerware).
* **Device Administrator Inspection**: Detects unauthorized apps registered under `DevicePolicyManager` preventing uninstallation.
* **Hidden Ghost App Finder**: Exposes stealth apps running background background services without home screen launcher icons.
* **Dangerous Permission Cluster Flags**: Flags high-risk permission combinations (Screen Overlay + SMS interception + Background location).
* **Instant Quarantine**: Safely freezes flagged apps in one command without host interaction.

### 🔄 5. Version-Aware Resilience & Reversibility (Android 6 to 17+)
* **Android 17+ (SDK 37+) Adaptation**: Automatically detects Android 17's hard-block on user-space system uninstalls and falls back gracefully to `disable-user`.
* **State Verification & Fallback Ladder**: Verifies resulting package states via `dumpsys package` to catch silent exit-code-0 failures on HyperOS and One UI.
* **Pre-Flight Snapshot Manifest**: Automatically creates a timestamped JSON backup manifest before any package modification.
* **1-Click Rollback**: Restore any or all packages at any time via `python scripts/restore.py --manifest latest`. Disabling is 100% data-preserving (app data remains intact).
* **Strict Allowlist**: Guaranteed preservation for OTA Update engines (`com.oplus.ota`, `com.google.android.configupdater`), OEM account logins (Samsung Account, HeyTap Cloud), banking apps, and Widevine L1 DRM.

### ⚡ 6. 2x Snappier UI Compositor
* Tunes Window Animation, Transition Animation, and Animator Duration scales from default `1.0x` to `0.5x` for instant touch and gesture feedback.
* Safely trims stale package caches without wiping user data.

### 📱 7. Multi-Device Audit Vault & Collision Prevention
* **Hardware Chip Fingerprinting**: Employs physical hardware serial numbers (`ro.serialno`) and Android installation IDs (`android_id`) to uniquely identify devices.
* **No Name Collision**: Prevents confusion when managing multiple family phones or client devices sharing the same model name.
* **Local Private Vault**: Tracks the history of fixes, benchmarks, and disabled packages per device locally (automatically gitignored for privacy).

---

## 📊 Real-World Benchmark Results

Tested on a budget device (**Redmi A1+ / Helio A22 / 2GB RAM** running Android 12 Go):

| Metric | Before Optimization | After Optimization | Real-World Impact |
| :--- | :--- | :--- | :--- |
| **Available Physical RAM** | `769.5 MB` | **`989.9 MB`** | **+220 MB free memory (+28.6% gain)** |
| **Active ZRAM / Swap** | `684.1 MB` | **`581.8 MB`** | **-102.3 MB swap pressure reclaimed** |
| **Kernel Swap Daemon (`kswapd0`)** | `2.5%` CPU | **`1.5%` CPU** | **-40% reduction in background thrashing** |
| **UI Animation Latency** | `1.0x` (Sluggish) | **`0.5x` (Snappy)** | **2x faster app opening & gesture speed** |
| **Lockscreen & Meta Ads** | Running 24/7 | **0 Wakelocks** | **Noticeably cooler phone & longer battery** |

---

## 📂 Repository Structure

```text
android-lag-fixer/
├── .github/workflows/ci.yml                 # Multi-OS GitHub Actions CI (Ubuntu, Windows, macOS)
├── pyproject.toml                           # Modern Python package specification (PEP 517/621)
├── LICENSE                                  # MIT Open Source License
├── README.md                                # Comprehensive user & developer guide
├── SKILL.md                                 # Agent Skill specification (Antigravity/Claude)
├── CONTRIBUTING.md                          # Contribution guidelines & fixture reporting
├── SECURITY.md                              # Security policy & isolation guarantees
├── package_database.json                    # Multi-tier risk catalog (Recommended, Advanced, Unsafe)
│
├── scripts/
│   ├── connect.py                           # Device connection & wireless pairing wizard
│   ├── diagnose.py                          # CPU load, ZRAM, memory pressure & process auditor
│   ├── operations.py                        # Verified state engine, fallback ladder & Android 17 resolution
│   ├── bench.py                             # Framestats jank ratio & 1% low FPS benchmark suite
│   ├── security_audit.py                    # Sketchy apps, accessibility hijackers & permission auditor
│   ├── optimize.py                          # Safe OEM debloater with automatic restore manifest
│   ├── restore.py                           # 1-click restore from manifest or package name
│   ├── compile_speed.py                     # ART AOT pre-compilation & reset point engine
│   ├── appops_restrict.py                   # AppOps background execution limits & standby bucket manager
│   ├── rescue.py                            # Emergency feature recovery & hardware safe mode rescue engine
│   ├── export_shizuku.py                    # On-device Shizuku / rish shell & paired rollback exporter
│   ├── update_database.py                   # Community UAD-ng debloat list merger & schema validator
│   ├── wizard.py                            # Unified interactive terminal control dashboard
│   ├── tweak_ui.py                          # 2x animation scaling & system cache trimmer
│   └── device_tracker.py                    # Hardware serial fingerprinting & multi-device audit vault
│
├── tests/
│   ├── test_operations.py                   # Automated unit tests for package mutations
│   ├── test_compile_speed.py                # Mocked tests for ART compilation & reset points
│   ├── test_appops_restrict.py              # Mocked tests for AppOps limits & standby buckets
│   ├── test_rescue.py                       # Mocked tests for emergency feature rescue & recovery
│   ├── test_export_shizuku.py               # Mocked tests for Shizuku & rollback shell exporter
│   ├── test_update_database.py              # Mocked tests for community list parsing & database merging
│   └── test_wizard.py                       # Mocked tests for terminal wizard & command formulation
│
└── references/
    ├── connection_guide.md                  # USB drivers, developer settings, wireless debugging
    ├── malware_and_security.md              # Technical breakdown of accessibility trojans & adware
    ├── virtual_ram_guide.md                 # zRAM CPU overhead and memory extension analysis
    ├── oem_catalogs.md                      # Samsung, Xiaomi, Realme, OnePlus bloat catalogs
    └── safety_matrix.md                     # Whitelist rules for 100% OTA, Banking & Account integrity
```

---

## 🛠️ Getting Started in 3 Steps

### ⚡ Fast-Track: Interactive Control Dashboard (Phase 4)
If you prefer an all-in-one interactive menu over typing individual command line flags, simply launch:
```bash
python scripts/wizard.py
```
*(Provides a guided numbered menu for diagnostics, frame pacing benchmarks, safe debloating, speed pre-compilation, AppOps limits, Shizuku export, and emergency rescue).*

### 📦 Optional: Install Globally via pipx / pip (Phase 5)
You can install and run `android-lag-fixer` directly as a standalone system command:
```bash
pipx install git+https://github.com/pavnxet/android-lag-fixer.git

# Run directly from anywhere in your terminal:
lagfixer         # Launches the interactive control dashboard
lagfixer-rescue  # Quick launcher for emergency rescue
lagfixer-bench   # Quick launcher for frame pacing benchmarks
```

### Prerequisites
* **Python 3.9+** installed on your PC (Windows, macOS, or Linux).
* **ADB (Android Debug Bridge)**:
  * Windows: Included with Android SDK Platform-Tools or standalone `adb.exe`.
  * macOS: `brew install android-platform-tools`
  * Linux: `sudo apt install adb`

---

### Step 1: Connect Your Phone (USB or Wireless)

#### Method A: USB Cable (Easiest)
1. On your phone: Go to **Settings** > **About Phone** > Tap **Build Number** (or **MIUI/OS Version**) **7 times** to unlock Developer Options.
2. Go to **Settings** > **Developer Options** > Toggle **ON**: **USB Debugging**.
3. Plug your phone into your PC with a data cable. Unlock your phone screen, check ☑ *"Always allow from this computer"*, and tap **OK**.
4. Test connection:
   ```bash
   python scripts/connect.py
   ```

#### Method B: Wireless Debugging (No Cable Needed, Android 11+)
1. Ensure your PC and phone are on the **same Wi-Fi network**.
2. Go to **Settings** > **Developer Options** > **Wireless Debugging** > Toggle **ON**.
3. Tap **"Pair device with pairing code"** to get the pairing IP, port, and 6-digit code.
4. Pair and connect from your terminal:
   ```bash
   python scripts/connect.py --pair 192.168.1.50:37891 123456
   python scripts/connect.py --connect 192.168.1.50:41235
   ```

---

### Step 2: Run Performance & Security Diagnostics

#### 1. Diagnose Root-Cause Lag & CPU Bottlenecks
```bash
python scripts/diagnose.py
```
*Profiles CPU run queues, checks memory pressure, and identifies top CPU-burning processes.*

#### 2. Run Baseline Frame Pacing Benchmark
```bash
python scripts/bench.py --app com.android.settings --duration 8 --save before.json
```
*Measures baseline UI frame pacing, jank percentage, P90 latency, and 1% Low FPS.*

#### 3. Audit Sketchy Apps & Accessibility Hijackers
```bash
python scripts/security_audit.py
```
*Audits third-party apps for accessibility abuse, hidden ghost launcher activities, and dangerous permission combinations.*

To safely quarantine/freeze any suspicious app immediately:
```bash
python scripts/security_audit.py --quarantine <package_name>
```

---

### Step 3: Optimize, Debloat & Speed Up

#### 1. Safe OEM Debloating & Telemetry Elimination
```bash
# Preview what would be disabled (safe dry run):
python scripts/optimize.py --profile auto --dry-run

# Apply optimizations:
python scripts/optimize.py --profile auto
```
*Options supported:*
* `--dry-run`: Preview changes without modifying device state.
* `--user <id>`: Target specific Android user profiles (default: `0`).
* `--update-db`: Automatically fetch and merge thousands of community-verified debloat entries from UAD-ng.
* `--profile`: Select `samsung`, `xiaomi`, `realme`, `google`, or `auto`.

#### 2. 2x UI Animation Speedup & Cache Trimming
```bash
python scripts/tweak_ui.py --scale 0.5 --trim-cache
```
*Cuts gesture navigation latency in half and trims stale system caches.*

#### 3. ART Ahead-Of-Time (AOT) Pre-Compilation & Reset Points
```bash
# Pre-compile hot code paths for all user apps to eliminate JIT launch stutter:
python scripts/compile_speed.py --all-user-apps --filter speed-profile

# Compile a specific heavy application for maximum execution performance:
python scripts/compile_speed.py --app com.android.settings --filter speed

# 1-Click Rollback / Reset Point (reverts packages back to default JIT state):
python scripts/compile_speed.py --reset-manifest compile_manifest_SM-G615F_YYYYMMDD_HHMMSS.json

# Or reset a single app:
python scripts/compile_speed.py --reset-app com.android.settings
```
*(Every compilation run automatically records a reset manifest in `backups/` and logs the event to your local device vault in `devices/<slug>/history.md`).*

#### 4. AppOps Background Execution Limits & Standby Buckets (Phase 2)
For apps you need to keep installed (e.g. Instagram, Facebook, Snapchat, Truecaller, shopping apps) but don't want draining CPU cycles, running background wakelocks, or polling telemetry while minimized:

```bash
# Restrict background execution for common social & battery hogs:
python scripts/appops_restrict.py --preset social --bucket restricted

# Restrict a specific package:
python scripts/appops_restrict.py --app com.instagram.android --mode ignore --bucket restricted

# Preview restrictions safely without modifying device:
python scripts/appops_restrict.py --preset social --dry-run

# 1-Click Rollback / Reset Point (restores original AppOps and standby states):
python scripts/appops_restrict.py --reset-manifest appops_manifest_SM-G615F_YYYYMMDD_HHMMSS.json

# Or restore background activity for a single app:
python scripts/appops_restrict.py --reset-app com.instagram.android
```
*(Every execution automatically captures a pre-flight snapshot manifest in `backups/` and logs the action to your local PC device vault).*

#### 5. Disable Memory Extension (On Your Phone)
* **Xiaomi / HyperOS / MIUI**: Settings > Additional Settings > Memory Extension > Select **Off** > Reboot.
* **Samsung One UI**: Settings > Battery and device care > Memory > RAM Plus > Select **Off** (or 0 GB unlocked by this tool) > Reboot.
* **Realme / Oppo / OnePlus**: Settings > About Device > RAM > Toggle OFF **RAM Expansion** > Reboot.

#### 6. Run Post-Optimization Benchmark & Prove Speedup
```bash
# Collect after benchmark:
python scripts/bench.py --app com.android.settings --duration 8 --save after.json

# Compare before vs after:
python scripts/bench.py --compare before.json after.json
```

#### 7. On-Device Shizuku & Rish Script Export (Phase 3)
For running optimizations or rollbacks directly on your phone without a PC connected (using Shizuku + Termux):

```bash
# Export matched optimization and rollback scripts for your OEM:
python scripts/export_shizuku.py --profile samsung
# (Supports: samsung, xiaomi, realme, google, social, all)

# Run on phone via Termux:
# 1. Start Shizuku via Wireless Debugging
# 2. In Termux, run: rish apply_optimization_samsung_TIMESTAMP.sh
# 3. 1-Click Rollback on phone: rish rollback_optimization_samsung_TIMESTAMP.sh
```

#### 8. Sync Community Package Database (Phase 4)
Automatically import and merge thousands of community-maintained, peer-reviewed debloat package definitions from UAD-ng (Universal Android Debloater Next Generation):

```bash
# Sync from upstream repository:
python scripts/update_database.py

# Import from a local JSON file (offline mode):
python scripts/update_database.py --file /path/to/uad_lists.json

# 1-Click Rollback if an update ever needs reverting:
python scripts/update_database.py --restore-backup package_database_backup_YYYYMMDD_HHMMSS.json
```
*(Every sync automatically validates package names against injection regex and creates a pre-flight backup snapshot in `backups/package_database_backup_*.json`).*

#### 9. Unified Interactive Terminal Control Wizard (Phase 4)
Run all tools, benchmarks, and recovery operations through a single interactive dashboard:

```bash
# Interactive menu:
python scripts/wizard.py

# Non-interactive CLI shortcut:
python scripts/wizard.py --action debloat --dry-run
python scripts/wizard.py --action rescue
```

---

### 🆘 Emergency Feature Rescue & Hardware Safe Mode Engine (Phase 3)

If any phone feature is restricted, broken, or misbehaving (e.g. Phone dialer, Google Play Services, Settings, Camera, SystemUI, Keyguard, or WebView):

```bash
# 1. Scan and instantly revive any disabled critical core components:
python scripts/rescue.py --fix-critical

# 2. Deep multi-layer rescue for a specific package (enables, reinstalls, resets AppOps, bucket & ART):
python scripts/rescue.py --rescue-package com.google.android.dialer

# 3. Re-enable all currently disabled packages across the user profile:
python scripts/rescue.py --restore-all-disabled

# 4. View all historical reset points and backup manifests:
python scripts/rescue.py --list-manifests

# 5. Display OEM-specific hardware Safe Mode / bootloop recovery key combinations:
python scripts/rescue.py --guide samsung    # Options: samsung, xiaomi, google, realme_oneplus, general
```
*(Every rescue operation automatically captures a pre-flight snapshot in `backups/rescue_snapshot_*.json` and logs the event to your local PC device vault).*

---

### 🔄 1-Click Rollback & Restoration

If you ever wish to re-enable an app or restore your phone to its exact pre-optimization state:

```bash
# Preview restoration without touching the device:
python scripts/restore.py --manifest latest --dry-run

# Restore everything from your latest optimization session:
python scripts/restore.py --manifest latest

# Or restore a specific package:
python scripts/restore.py --package com.example.app
```

---

### 📱 Multi-Device Audit Tracker (For Families & Tech Enthusiasts)

Manage multiple devices and track past fixes over time without name collisions:

```bash
# Inspect currently connected device and view its past audit history:
python scripts/device_tracker.py --status

# List all tracked devices in your private local vault:
python scripts/device_tracker.py --list
```

*(Note: The `devices/` and `backups/` directories store your private hardware serials and snapshots locally and are automatically ignored by git to protect your privacy).*

---

## 🛡️ Supported OEMs & Profiles

* **Samsung (One UI)**: McAfee Device Security, Game Launcher ads, Bixby telemetry, RAM Plus.
* **Xiaomi (MIUI & HyperOS)**: MIUI System Ads (MSA), Analytics daemon, Wallpaper Carousel / Glance lockscreen ads, Joyose throttling, App Mall pushers.
* **Realme / Oppo / OnePlus (ColorOS / OxygenOS)**: HeyTap notification wakelocks, ColorOS telemetry (`com.oplus.statistics.rom`), DeepThinker tracking, Oplus Commercial ads.
* **Universal Social Bloat**: Pre-installed Meta/Facebook background daemons (`com.facebook.system`, `com.facebook.appmanager`, `com.facebook.services`, `com.facebook.katana`).
* **Critical Subsystems Allowlist**: Guaranteed preservation for Google Play Services, Android System WebView, OTA updaters, Telephony/Emergency dialers, and Banking apps.

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting verified OEM packages and benchmark reports.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE). Free for personal and commercial use.
