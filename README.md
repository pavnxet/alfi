# 📱 Android Lag Fixer & Performance Optimizer (Non-Root ADB)

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Android_9_--_15-3DDC84?style=for-the-badge&logo=android&logoColor=white" alt="Android 9 to 15" />
  <img src="https://img.shields.io/badge/Requirement-No_Root_Required-blue?style=for-the-badge" alt="No Root Required" />
  <img src="https://img.shields.io/badge/Safety-100%25_Reversible-success?style=for-the-badge" alt="100% Reversible" />
  <img src="https://img.shields.io/badge/Host_PC_Risk-Zero_Malware_Risk-green?style=for-the-badge" alt="Zero Malware Risk" />
  <img src="https://img.shields.io/badge/License-MIT-orange?style=for-the-badge" alt="MIT License" />
</p>

<p align="center">
  <strong>The definitive open-source Android lag fix, safe OEM debloater, Virtual RAM eliminator, and security audit toolkit.</strong><br />
  <em>Diagnose CPU bottlenecks, eliminate flash-memory thrashing, detect accessibility trojans and ghost adware, and boost UI responsiveness via standard ADB text streams.</em>
</p>

---

## ⚡ Why Do Android Phones Lag Over Time?

Most Android speedup guides recommend aggressive factory resets, third-party "cleaner" apps (which are often adware themselves), or risky root modifications that trip Knox, Widevine L1, and banking security.

In reality, Android lag and micro-stutters stem from 4 distinct kernel and userland bottlenecks:

1. **Virtual RAM / Memory Extension Thrashing**: OEMs (Samsung, Xiaomi, Realme, OnePlus) page compressed memory directly to slow internal eMMC/UFS flash storage. When memory is full, the kernel falls into uninterruptible sleep state `D` waiting for flash I/O (`kswapd0` and `f2fs_gc`), triggering 1–2 second UI freezes.
2. **Aggressive Background Telemetry & Adware**: Hidden OEM daemons (Glance wallpaper carousels, Xiaomi analytics, Meta/Facebook pre-installed app installers, HeyTap MCS) wake the CPU hundreds of times per hour, preventing deep-sleep C-states and causing thermal throttling.
3. **Accessibility Service & Permission Abuse**: Rogue apps, ghost background services, and banking trojans exploit `BIND_ACCESSIBILITY_SERVICE` and overlay privileges (`SYSTEM_ALERT_WINDOW`), intercepting compositors and causing thousands of page faults.
4. **Sluggish Default UI Animation Scales**: Default `1.0x` window, transition, and animator scales add artificial latency to gesture navigation and app launch animations.

**Android Lag Fixer** solves all four bottlenecks at the root level using non-destructive, non-root ADB protocols.

---

## 🚀 Key Features & Capabilities

### 🛡️ 1. Absolute Host PC Protection
* **Zero Binary Execution on Host**: The toolkit **never downloads, mounts, or executes Android binaries (`.apk`, `.dex`, `.so`) on your PC**.
* **Pure ADB Text Stream Auditing**: All scans, permission audits, and telemetry freezes execute remotely inside the Android userland using standard, sandboxed ADB shell commands (`dumpsys`, `pm`, `settings`).

### 🔍 2. Deep Root-Cause Performance Diagnostics
* **True Kernel Run-Queue Profiling**: Measures 1m, 5m, and 15m CPU load averages to identify thermal saturation.
* **Infamous Background Hogs Detection**: Automatically detects notorious CPU loopers (Microsoft Link to Windows looping at >100% CPU, McAfee Device Security, MacroDroid compositor hooks).
* **ZRAM & Flash I/O Wait Analysis**: Analyzes memory pressure, active swap saturation, and flash garbage collection lockups.

### 🕵️ 3. Security & Sketchy Apps Auditor
* **Accessibility Service Hijackers**: Audits apps holding screen-reading and click-simulation permissions (primary vector for banking trojans and stalkerware).
* **Device Administrator Inspection**: Detects unauthorized apps registered under `DevicePolicyManager` preventing deletion.
* **Hidden Ghost App Finder**: Exposes stealth apps running background background services without home screen launcher icons.
* **Dangerous Permission Cluster Flags**: Flags high-risk permission combinations (Screen Overlay + SMS interception + Background location).
* **Instant Quarantine**: Safely freezes flagged apps in one command without host interaction.

### 🔄 4. 100% Reversible & Disaster-Free (OTA Safe)
* **User-Space Freeze**: Uses `pm disable-user --user 0 <pkg>` instead of destructive system partition deletions.
* **Pre-Flight Snapshot Manifest**: Automatically creates a timestamped JSON backup manifest before any package modification.
* **1-Click Rollback**: Restore any or all packages at any time via `python scripts/restore.py --manifest latest`.
* **Zero Brick Guarantee**: Strict whitelist protects OTA Update engines (`com.oplus.ota`, `com.google.android.configupdater`), OEM account logins (Samsung Account, HeyTap Cloud), banking apps, and Widevine L1 DRM.

### ⚡ 5. 2x Snappier UI Compositor
* Tunes Window Animation, Transition Animation, and Animator Duration scales from default `1.0x` to `0.5x` for instant touch and gesture feedback.
* Safely trims stale package caches without wiping user data.

### 📱 6. Multi-Device Audit Vault & Collision Prevention
* **Hardware Chip Fingerprinting**: Employs physical hardware serial numbers (`ro.serialno`) and Android installation IDs (`android_id`) to uniquely identify devices.
* **No Name Collision**: Prevents confusion when managing multiple family phones or client devices sharing the same model name.
* **Local Private Vault**: Tracks the history of fixes, benchmarks, and disabled packages per device locally (never committed to public repos).

---

## 📊 Real-World Benchmark Results

Tested on a low-end budget device (**Redmi A1+ / Helio A22 / 2GB RAM** running Android 12 Go):

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
├── LICENSE                                  # MIT Open Source License
├── README.md                                # Comprehensive guide & documentation
├── SKILL.md                                 # Agent Skill specification (Antigravity/Claude)
├── package_database.json                    # Multi-tier risk catalog (Recommended, Advanced, Unsafe)
│
├── scripts/
│   ├── connect.py                           # Device connection & wireless pairing wizard
│   ├── diagnose.py                          # CPU load, ZRAM, flash thrashing & process auditor
│   ├── security_audit.py                    # Sketchy apps, accessibility hijackers & permission auditor
│   ├── optimize.py                          # Safe OEM debloater with automatic restore manifest
│   ├── restore.py                           # 1-click restore from manifest or package name
│   ├── tweak_ui.py                          # 2x animation scaling & system cache trimmer
│   └── device_tracker.py                    # Hardware serial fingerprinting & multi-device audit vault
│
└── references/
    ├── connection_guide.md                  # USB drivers, developer settings, wireless debugging
    ├── malware_and_security.md              # Technical breakdown of accessibility trojans & adware
    ├── virtual_ram_guide.md                 # Why RAM expansion causes storage wear & UI stutters
    ├── oem_catalogs.md                      # Samsung, Xiaomi, Realme, OnePlus bloat catalogs
    └── safety_matrix.md                     # Whitelist rules for 100% OTA, Banking & Account integrity
```

---

## 🛠️ Getting Started in 3 Steps

### Prerequisites
* **Python 3.8+** installed on your PC (Windows, macOS, or Linux).
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
*Profiles CPU run queues, checks if Virtual RAM is thrashing flash storage, analyzes ZRAM, and identifies top CPU-burning processes.*

#### 2. Audit Sketchy Apps & Accessibility Hijackers
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
python scripts/optimize.py --profile auto
```
*Automatically detects your hardware manufacturer (Samsung, Xiaomi, Realme, OnePlus, Oppo, Google, or Universal), creates a pre-flight restore manifest in `backups/`, and disables safe telemetry and ad pushers.*

#### 2. 2x UI Animation Speedup & Cache Trimming
```bash
python scripts/tweak_ui.py --scale 0.5 --trim-cache
```
*Cuts gesture navigation latency in half and trims stale system caches.*

#### 3. Disable Virtual RAM / RAM Expansion (On Your Phone)
* **Xiaomi / HyperOS / MIUI**: Settings > Additional Settings > Memory Extension > Select **Off** > Reboot.
* **Samsung One UI**: Settings > Battery and device care > Memory > RAM Plus > Select **Off** (or 0 GB unlocked by this tool) > Reboot.
* **Realme / Oppo / OnePlus**: Settings > About Device > RAM > Toggle OFF **RAM Expansion** > Reboot.

---

### 🔄 1-Click Rollback & Disaster-Free Restoration

If you ever wish to re-enable an app or restore your phone to its exact pre-optimization state:

```bash
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
* **Critical Subsystems Whitelist**: Guaranteed 100% preservation for Google Play Services, Android System WebView, OTA updaters, Telephony/Emergency dialers, and Banking apps.

---

## 🤝 Contributing

Contributions are welcome! If you know of OEM-specific bloatware packages, battery drain culprits, or performance tweaks:
1. Fork the repository.
2. Add verified packages and risk classifications to `package_database.json`.
3. Submit a Pull Request.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE). Free for personal and commercial use.

---

<p align="center">
  <sub>Built with care for a faster, cooler, and cleaner Android experience.</sub>
</p>
