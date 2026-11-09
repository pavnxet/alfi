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
│   ├── tweak_ui.py                          # 2x animation scaling & system cache trimmer
│   └── device_tracker.py                    # Hardware serial fingerprinting & multi-device audit vault
│
├── tests/
│   └── test_operations.py                   # Automated unit test suite
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

#### 3. Disable Memory Extension (On Your Phone)
* **Xiaomi / HyperOS / MIUI**: Settings > Additional Settings > Memory Extension > Select **Off** > Reboot.
* **Samsung One UI**: Settings > Battery and device care > Memory > RAM Plus > Select **Off** (or 0 GB unlocked by this tool) > Reboot.
* **Realme / Oppo / OnePlus**: Settings > About Device > RAM > Toggle OFF **RAM Expansion** > Reboot.

#### 4. Run Post-Optimization Benchmark & Prove Speedup
```bash
# Collect after benchmark:
python scripts/bench.py --app com.android.settings --duration 8 --save after.json

# Compare before vs after:
python scripts/bench.py --compare before.json after.json
```

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
