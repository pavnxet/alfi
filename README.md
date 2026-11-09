<p align="center">
  <img src="assets/alfi_poster.webp" alt="ALFi - open-source Android lag fixer, debloater and security auditor using ADB with no root" width="750" />
</p>

<h1 align="center">⚡ ALFi — Android Lag Fixer, Debloater & Security Auditor</h1>

<p align="center">
  <strong>Fix a slow, laggy Android phone over ADB — no root, fully reversible, and proven with real benchmark data.</strong>
</p>

<p align="center">
  <a href="https://github.com/pavnxet/alfi/actions/workflows/ci.yml">
    <img src="https://github.com/pavnxet/alfi/actions/workflows/ci.yml/badge.svg" alt="CI Status" />
  </a>
  <img src="https://img.shields.io/badge/Release-v1.2.0-00b0ff?style=flat&logo=github" alt="Release v1.2.0" />
  <img src="https://img.shields.io/badge/Tests-107%20Passed-success?style=flat" alt="107 Tests Passing" />
  <img src="https://img.shields.io/badge/Platform-Android_9_--_17+-3DDC84?style=flat&logo=android&logoColor=white" alt="Android 9 to 17+" />
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white" alt="Python 3.9+" />
  <img src="https://img.shields.io/badge/Root-No_Root_Required-blue?style=flat" alt="No Root Required" />
  <img src="https://img.shields.io/badge/Safety-Disables_Preserve_Data-success?style=flat" alt="Safe and Reversible" />
  <img src="https://img.shields.io/badge/CLI-alfi-00e676?style=flat" alt="CLI Command" />
  <img src="https://img.shields.io/badge/License-MIT-orange?style=flat" alt="MIT License" />
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> ·
  <a href="#features">Features</a> ·
  <a href="#real-world-benchmark-results">Benchmarks</a> ·
  <a href="#the-4-optimization-modes">Modes</a> ·
  <a href="#security-and-malware-auditing">Security Audit</a> ·
  <a href="#safety-rollback-and-rescue">Rollback</a> ·
  <a href="#faq">FAQ</a>
</p>

---

**ALFi (Android Lag Fixer)** is a free, open-source Python toolkit that speeds up slow Android phones using nothing but standard **ADB** (Android Debug Bridge) commands. It diagnoses *why* your phone lags, safely **disables OEM bloatware and background telemetry**, tunes **zRAM / virtual RAM pressure**, speeds up **UI animations**, and **audits your device for accessibility-service trojans, ghost adware and stalkerware** — then proves the improvement with real frame-pacing and battery measurements.

It works on **Samsung (One UI), Xiaomi (MIUI / HyperOS), Realme / Oppo / OnePlus (ColorOS / OxygenOS) and stock Google Pixel** devices, requires **zero root**, has **zero external pip dependencies** (100% Python standard library), and every change can be undone with a single command.

### At a Glance

| | |
| :--- | :--- |
| **What it fixes** | UI stutter, slow app launches, high CPU load, memory pressure, background battery drain, adware, OEM telemetry |
| **What you need** | A PC (Windows / macOS / Linux) with Python 3.9+ and ADB, plus a phone with USB or Wireless Debugging on |
| **Dependencies** | **Zero pip dependencies** — 100% pure Python standard library |
| **Root required?** | **No** — standard non-root ADB text protocol only |
| **Is it reversible?** | **Yes** — packages are *disabled*, not deleted. Manifest is saved & `fsync`ed before the first change |
| **Does it prove results?** | **Yes** — before/after frame pacing (1% low FPS, jank %), RAM, swap, CPU load and wakelock audits |
| **Supported Android** | Android 9 – 17+ (also validated on Android 8.1) |

---

## Quick Start

```bash
# 1. Install (needs Python 3.9+ and ADB on your PC)
pipx install git+https://github.com/pavnxet/alfi.git

# 2. Plug in your phone with USB Debugging enabled, then launch the dashboard
alfi

# 3. Or run the recommended optimization directly (preview first, then apply)
alfi-modes --mode medium --dry-run
alfi-modes --mode medium
```

> **Something went wrong?** Undo everything from your latest session with `python scripts/restore.py --manifest latest`.
> New to ADB? Follow the [step-by-step connection guide](#step-1-connect-your-phone).

---

## Table of Contents

- [Why Do Android Phones Lag Over Time?](#why-do-android-phones-lag-over-time)
- [Features](#features)
- [Real-World Benchmark Results](#real-world-benchmark-results)
- [The 4 Optimization Modes](#the-4-optimization-modes)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
- [Security and Malware Auditing](#security-and-malware-auditing)
- [Safety, Rollback and Rescue](#safety-rollback-and-rescue)
- [Under the Hood: Advanced Engines](#under-the-hood-advanced-engines)
- [Compatibility](#compatibility)
- [How ALFi Compares](#how-alfi-compares)
- [FAQ](#faq)
- [Repository Structure](#repository-structure)
- [Contributing, Security and License](#contributing-security-and-license)

---

## One command for everything

Every capability is reachable as `alfi <command>`, so nothing needs a separate
script name or a remembered path.

```bash
alfi                        # interactive dashboard
alfi status                 # one line: device, Android, transport, battery
alfi modes --mode low       # pre-flight -> confirm -> apply
alfi bench --app com.android.settings
alfi doze --clean
alfi restore --manifest latest
```

| Group | Commands |
| --- | --- |
| Core | `status`, `watch`, `probe`, `attrib`, `devices`, `tui` |
| Optimise | `modes`, `optimize`, `ui`, `compile`, `appops`, `doze` |
| Measure | `diagnose`, `bench`, `power`, `audit`, `vault` |
| Recover | `restore`, `rescue`, `shizuku` |
| Maintain | `update`, `config` |

Flags pass straight through to the underlying engine, so `--dry-run`, `--json`,
`--yes`, `--user` and `--device` behave the same everywhere.

### Measure what the phone is actually waiting on

```bash
alfi probe      # stall time (PSI), thermal status, memory truth, battery
alfi attrib     # runaway processes, dexopt state, wakeup counts
```

`probe` reads `/proc/pressure/*` — the same counters Android's own low-memory
killer uses — so it can tell you **"memory is not your problem"** instead of
showing 84% RAM and letting you guess. It also reports thermal throttling
(honouring `IsStatusOverride`) and falls back to `/proc/vmstat` on kernels
without PSI.

`attrib` answers *who*: the largest resident processes (flagging one that eats
a quarter of RAM), which apps are still interpreted (`status=verify`), and
per-package wakeups. Both support `--json`.

### Live monitor

```bash
alfi watch                 # redraws every 1.5s: CPU, memory, swap/zram, battery, top process
alfi watch --interval 3    # slower refresh
alfi watch --json          # one snapshot as JSON, then exit (script-friendly)
```

In a terminal it is a full-screen panel with block meters and a CPU sparkline;
piped or redirected it prints one snapshot and exits, so it never loops in a
log or CI job.

### Themes and glyphs

```bash
alfi config set theme amber   # neon (default) | amber | mono
alfi config set ascii true    # ASCII borders and icons instead of unicode
alfi config set color never   # no escape sequences at all
```

The palette is resolved once per process (`ALFI_THEME`, `ALFI_ASCII`, `NO_COLOR`),
so every screen — dashboard, pre-flight card, monitor — follows it.

### Saved defaults

Set once, stop repeating flags:

```bash
alfi config set mode medium     # `alfi modes` now defaults to Medium
alfi config set device 192.168.1.42:5555
alfi config set color never     # plain output, no escapes
alfi config                      # show current defaults
alfi config path                 # ~/.config/alfi/config.json
```

Defaults live in one JSON file (`$ALFI_CONFIG`, else `$XDG_CONFIG_HOME/alfi/config.json`,
else `~/.config/alfi/config.json`) and are applied as environment variables and
injected flags — never as hidden behaviour. An explicit flag always wins.

## Terminal UI

ALFi renders its interface from a small standard-library layer in `scripts/ui/`, so the
same screens work in a full-colour terminal, a plain pipe, and everything in between.

| Environment | What you get |
| --- | --- |
| Interactive terminal | rounded boxes, colour, emoji icons, live progress bar |
| `NO_COLOR=1` or `TERM=dumb` | same layout, no escape sequences |
| Piped / redirected (`\| tee`, CI logs) | ASCII borders (`+--+`), no icons, one line per event |
| Narrow terminal (< 60 columns) | compact banner, boxes clamped to the terminal width |
| `ALFI_ASCII=1` | forces the ASCII renderer even on a capable terminal |

Width is measured in **display columns**, not characters: ANSI escapes count as zero and
emoji count as two, so borders stay aligned on every row.

```bash
alfi                     # dashboard
alfi-modes --mode low    # pre-flight card -> confirm -> progress -> session summary
NO_COLOR=1 alfi          # plain output
```

Nothing in `scripts/ui/` imports a third-party package, calls `adb`, or writes outside
`ui.out()`.

## Why Do Android Phones Lag Over Time?

Most Android speed-up advice falls into three bad categories: factory resets, third-party "cleaner" apps (which are frequently adware themselves), or rooting, which can trip Knox, Widevine L1 and banking-app security checks.

In practice, Android lag and micro-stutter usually come from **four distinct bottlenecks**:

| # | Bottleneck | What actually happens | Typical symptom |
| :-: | :--- | :--- | :--- |
| 1 | **zRAM compression overhead** | OEM "virtual RAM" features (Samsung RAM Plus, Xiaomi Memory Extension, Realme RAM Expansion) push more pages into compressed in-memory swap. On weak mid-range and budget CPUs (Cortex-A53 / A55), `kswapd0` burns CPU on LZ4 / ZSTD compression and competes with the UI thread. | 1–2 second touch stutters, slow app switching |
| 2 | **Background telemetry and adware** | Hidden OEM daemons (Glance wallpaper carousels, Xiaomi analytics, pre-installed Meta / Facebook installers, HeyTap MCS) wake the CPU hundreds of times per hour, blocking deep-sleep states. | Heat, thermal throttling, battery drain |
| 3 | **Accessibility and overlay abuse** | Rogue apps and banking trojans abuse `BIND_ACCESSIBILITY_SERVICE` and `SYSTEM_ALERT_WINDOW`, hooking the window manager and triggering thousands of compositor page faults. | Random lag, phantom taps, security risk |
| 4 | **Slow default animation scales** | Default `1.0x` window, transition and animator scales add artificial latency to gestures and app launches. | Phone *feels* slow even when it isn't |

ALFi addresses each of these with **non-destructive, non-root ADB commands**.

---

## Features

### 🔍 Root-Cause Performance Diagnostics
- **Kernel run-queue profiling** — measures 1m / 5m / 15m CPU load averages to separate real saturation from noise.
- **Background hog detection** — flags notorious CPU loopers such as Microsoft *Link to Windows* (>100% CPU), McAfee Device Security and MacroDroid compositor hooks.
- **zRAM memory-pressure analysis** — inspects RAM headroom, swap compression saturation and `kswapd0` activity.

### 🏁 Objective Frame-Pacing and Jank Benchmarking
- Measures real frame durations from the graphics compositor via `dumpsys gfxinfo framestats`.
- **Automated swipe gestures** — automatically executes smooth hardware scroll gestures over ADB so stationary screens capture 200–400 frames reliably without manual touch input.
- **Refresh-rate aware** (60 / 90 / 120 / 144 Hz) — jank thresholds are dynamically calculated per display (19.1 ms @ 60 Hz, 12.8 ms @ 90 Hz, 9.6 ms @ 120 Hz).
- Reports **1% Low FPS**, P50 / P90 / P99 latency and dropped-frame counts.
- **Before-vs-after comparison:** `python scripts/bench.py --compare before.json after.json`.

### 🕵️ Security and Sketchy-App Auditing
- Accessibility-service hijacker detection (the main vector for banking trojans such as TeaBot, and for stalkerware).
- Device Administrator inspection for apps that block uninstallation.
- Ghost-app finder for background services with no launcher icon.
- Dangerous permission-cluster flags (screen overlay + SMS interception + background location).
- One-command **quarantine** (freeze) of any flagged app.

### 🧹 Safe OEM Debloating
- Profiles for Samsung, Xiaomi, Realme / Oppo / OnePlus and Google, plus an `auto` detector.
- A **package dependency graph** blocks disabling anything other apps rely on.
- Community package definitions can be merged from [UAD-ng](https://github.com/Universal-Debloater-Alliance/universal-android-debloater-next-generation) with schema validation.

### 🔄 Version-Aware Resilience
- **Android 17+ (SDK 37+):** detects the hard block on user-space system uninstalls and falls back to `disable-user`.
- **State verification and fallback ladder:** prioritizes per-user `pm list packages -e/-d/-u` and falls back to `dumpsys package` to catch silent "exit code 0" failures on HyperOS and One UI.
- **Strict allowlist:** OTA engines (`com.oplus.ota`, `com.google.android.configupdater`), OEM account logins (Samsung Account, HeyTap Cloud), banking apps and Widevine L1 DRM are always preserved.

### ⚡ Snappier UI and Battery
- Window, transition and animator scales tuned from `1.0x` to `0.5x`.
- Safe trimming of stale package caches without wiping user data.
- Deep Doze enforcement and wakelock reduction, with measurable battery proof.

### 🛡️ Host PC Isolation
- **ALFi never downloads, mounts or executes Android binaries (`.apk`, `.dex`, `.so`) on your computer.**
- All scans, permission audits and telemetry freezes run *inside* the phone through sandboxed ADB shell text streams (`dumpsys`, `pm`, `settings`).

### 📱 Multi-Device Audit Vault
- Devices are identified by hardware serial (`ro.serialno`) and `android_id`, so two phones of the same model never collide.
- Fix history, benchmarks and disabled packages are tracked per device in a local vault that is **gitignored by default**.

---

## Real-World Benchmark Results

Measured with ALFi's own diagnostics before and after optimization.

### Device 1 — Budget Entry Phone
**Redmi A1+ · Helio A22 · 2 GB RAM · Android 12 Go**

| Metric | Before | After | Impact |
| :--- | :--- | :--- | :--- |
| **Available physical RAM** | `769.5 MB` | **`989.9 MB`** | **+220 MB free (+28.6%)** |
| **Active zRAM / swap** | `684.1 MB` | **`581.8 MB`** | **−102.3 MB swap pressure** |
| **`kswapd0` CPU usage** | `2.5%` | **`1.5%`** | **−40% background thrashing** |
| **UI animation scale** | `1.0x` | **`0.5x`** | **~2x faster app opening and gestures** |
| **Lockscreen and Meta ad services** | Running 24/7 | **0 wakelocks** | **Cooler phone, longer battery** |

### Device 2 — Legacy Samsung Phone
**Galaxy J7 Max · SM-G615F · 4 GB RAM · Android 8.1.0**

| Metric | Before | After | Impact |
| :--- | :--- | :--- | :--- |
| **System server CPU load** | `152%` (thermal throttling) | **`31%`** | **−79.6% core OS CPU use** |
| **Google Play Services CPU** | `133%` | **`24%`** | **−82.0% background polling** |
| **IronSource Aura OEM adware** | `9.4%` (looping) | **Killed (0%)** | **Rogue app-installer eliminated** |
| **Available physical RAM** | `2078.7 MB` | **`2131.0 MB`** | **+52.3 MB headroom** |
| **1-minute CPU load average** | `16.86` (extreme saturation) | **`11.04`** | **−34.5% system load** |

> Results vary by device, OEM and installed apps. Run your own before/after with `bench.py` — see [Benchmark Your Phone](#3-benchmark-before-and-after).

---

## The 4 Optimization Modes

ALFi is **mode-first**: you choose a calibrated risk tier instead of guessing which tweaks to run. Anything high-risk is quarantined inside **Ultra** behind explicit confirmation gates and dependency-graph checks.

```text
╭────────────────────────────────────────────────────────────────────────╮
│                 ⚡ CHOOSE OPTIMIZATION ARCHITECTURE ⚡                 │
╰────────────────────────────────────────────────────────────────────────╯

  [ 1 ] 🟢 LOW MODE ─────── SAFE BASELINE (Zero Risk)
        • Scope   : Carrier adware stubs, 0.75x animations, stale cache trim
        • Target  : Family phones, work profiles, zero tolerance for feature changes

  [ 2 ] 🟡 MEDIUM MODE ──── BALANCED DAILY DRIVER (Recommended)
        • Scope   : Low + OEM telemetry (Glance, Meta, MSA), 0.5x animations,
                    ART speed-profile on top user apps, social AppOps limits
        • Target  : Everyday smartphones wanting snappy UI & cooler battery

  [ 3 ] 🟠 HIGH MODE ────── AGGRESSIVE ACCELERATION (Sluggish/Budget Devices)
        • Scope   : Medium + vendor bloat (Bixby, Joyose), App Standby RESTRICTED,
                    Deep Doze allowlist cleanup, Virtual RAM off guidance
        • Target  : Power users, older devices, budget 2GB-4GB hardware with lag

  [ 4 ] 🔴 ULTRA MODE ───── EXTREME STRIP-DOWN (High-Risk / Power Users)
        • Scope   : High + duplicate OEM accounts (Samsung/Mi ID), duplicate stores,
                    secondary keyboards/launchers, 0.0x zero animations, full AOT
        • Safety  : Double-Gate: Dependency Graph Check + Requires 'I UNDERSTAND'

  [ 0 ] 🔙 Return to Main Menu
──────────────────────────────────────────────────────────────────────────
```

### Pre-Flight Optimization Audit Report Gate
Before any optimization touches your phone, ALFi scans your device and renders a transparent pre-flight report card:

```text
╭────────────────────────────────────────────────────────────────────────╮
│  📋 PRE-FLIGHT OPTIMIZATION AUDIT REPORT : [🟡 MEDIUM (BALANCED)]      │
╰────────────────────────────────────────────────────────────────────────╯

  • Target Device      : REALME RMX3867 (Android 16, SDK 36)
  • Debloat Candidates : 6 bloatware & telemetry packages identified
  • AppOps Restrictions: 3 background hogs (Instagram, Twitter, Truecaller)
  • UI Animation Scale : Set to 0.5x (2x snappier gesture response)
  • Cache Maintenance  : Trim stale system caches without data loss
  • ART Pre-Compile    : Speed-profile AOT compilation on 3 top apps
  • Rollback Safety Net: Snapshot manifest written & fsynced before first mutation
──────────────────────────────────────────────────────────────────────────

  [ Y ] ✅ Confirm and Apply Optimization
  [ D ] 🔍 View Detailed Package List (Names & Explanations)
  [ N ] 🚪 Cancel and Return to Menu (No changes made)
──────────────────────────────────────────────────────────────────────────
```

- Press **`Y`** to confirm and apply.
- Press **`D`** to inspect the full list of detected packages, package explanations, and AppOps throttles.
- Press **`N`** to abort cleanly with zero modifications.
- Running headless or in CI? Pass `--yes` to acknowledge unattended execution.

<details>
<summary><strong>📋 Detailed mode comparison matrix (click to expand)</strong></summary>

| Feature / Vector | 🟢 Low | 🟡 Medium (Recommended) | 🟠 High | 🔴 Ultra |
| :--- | :--- | :--- | :--- | :--- |
| **Philosophy** | Zero risk; safe for family and work profiles. | Balanced daily driver; no ad tracking, no micro-stutter, no feature loss. | Aggressive smoothness and battery for 2–4 GB / older hardware. | Maximum strip-down for gaming benchmarks and secondary devices. |
| **Packages disabled** | Carrier bloat and marketing preloads (`Recommended`: Aura, carrier stubs). | Low + OEM telemetry and tracking (`Recommended`: Glance, MSA, Meta). | Medium + non-critical vendor bloat (`Advanced`: Bixby, AR Emoji, Joyose). | High + OEM cloud sync, duplicate stores, secondary keyboards / launchers (`Expert`). |
| **AppOps background limits** | Untouched. | `RUN_IN_BACKGROUND=ignore` on social / shopping hogs (Facebook, Instagram, Truecaller). | Background execution blocked on all detected non-essential apps. | Maximum background freeze across third-party apps. |
| **App Standby buckets** | Untouched. | `rare` for social / shopping pollers. | `restricted` (Android 12+). | `restricted` for all non-system user apps. |
| **ART AOT pre-compile** | Default JIT. | `speed-profile` on top foreground apps. | `speed` on heavy apps and launcher. | Full system and user `speed` compilation. |
| **Animations** | `0.75x` | `0.5x` | `0.5x` | `0.0x` (off) |
| **Doze and battery** | Untouched. | Clean telemetry pollers from `deviceidle whitelist`. | Rapid Deep Doze on screen-off + allowlist cleanup. | Forced Deep Doze + stripped allowlist + alarm caps. |
| **Virtual RAM (zRAM / RAM Plus)** | Untouched. | Untouched. | Guided disable in Settings. | Full disable guidance (zero paging latency). |
| **Safety gate** | Pre-flight audit report. | Pre-flight audit report. | Pre-flight manifest + summary preview. | **Double gate:** dependency-graph validation + typing `I UNDERSTAND`. |

</details>

```bash
python scripts/modes.py                       # interactive mode picker
python scripts/modes.py --mode medium         # run a specific mode with audit gate
python scripts/modes.py --mode high --dry-run # preview without changing anything
python scripts/modes.py --mode medium --yes   # unattended automated run
python scripts/modes.py --mode ultra --force-ultra
```

---

## Installation

### Prerequisites

| Requirement | Details |
| :--- | :--- |
| **Python** | 3.9+ (CI-tested on 3.10 – 3.13 across Ubuntu, Windows and macOS) |
| **Dependencies** | **Zero third-party pip dependencies** — uses 100% Python standard library (`subprocess`, `re`, `json`, `os`, `shutil`) |
| **ADB** | Windows: Android SDK Platform-Tools or standalone `adb.exe` · macOS: `brew install android-platform-tools` · Linux: `sudo apt install adb` |
| **Phone** | Developer Options enabled with USB Debugging (or Wireless Debugging on Android 11+) |

### Option A — Install globally with pipx (recommended)

```bash
pipx install git+https://github.com/pavnxet/alfi.git
```

This installs the following global CLI commands:

| Command | Purpose |
| :--- | :--- |
| `alfi` | Interactive control dashboard |
| `alfi-modes` | 4-tier optimization modes (Low / Medium / High / Ultra) |
| `alfi-power` | Battery drain and wakelock proof |
| `alfi-doze` | Deep Doze and `deviceidle` allowlist cleaner |
| `alfi-bench` | Frame-pacing and jank benchmark suite |
| `alfi-rescue` | Emergency rescue launcher |
| `alfi -s <serial>` | Target a specific USB or wireless device |

### Option B — Run from source

```bash
git clone https://github.com/pavnxet/alfi.git
cd alfi
python scripts/wizard.py
```

### The Interactive Dashboard

Prefer menus over flags? Run `alfi` (or `python scripts/wizard.py`) for a guided, cyber-themed dashboard covering modes, diagnostics, benchmarks, debloating, pre-compilation, AppOps limits, Shizuku export, screen mirroring and multi-device switching.

Press **`D`** to open the **Device Manager**: list attached devices, check authorization state (with guidance for pending RSA prompts), pair Android 11+ phones with a 6-digit code, or switch targets on the fly.

```text
╭────────────────────────────────────────────────────────────────────────╮
│               ⚡ ALFi DEVICE MANAGER & TARGET SELECTOR ⚡               │
╰────────────────────────────────────────────────────────────────────────╯
  [ 1 ] 🟢 ACTIVE TARGET : SAMSUNG GALAXY S23 (USB)
  [ 2 ] ⚪ AVAILABLE     : REDMI 220733SI (WIRELESS - 192.168.1.55:5555)
  [ R ] 🔄 Refresh Device Scan
  [ W ] 📶 Pair / Connect Wireless Phone (IP:Port + Pairing Code)
  [ 0 ] 🔙 Return to Dashboard
```

### Step 1: Connect Your Phone

**Method A — USB cable (easiest)**

1. On the phone, open **Settings → About Phone** and tap **Build Number** (or **MIUI / OS Version**) **7 times** to unlock Developer Options.
2. Open **Settings → Developer Options** and enable **USB Debugging**.
3. Connect with a *data* cable, unlock the screen, tick **"Always allow from this computer"** and tap **OK**.
4. Verify the connection:

   ```bash
   python scripts/connect.py
   ```

**Method B — Wireless Debugging (no cable, Android 11+)**

1. Put the PC and phone on the **same Wi-Fi network**.
2. Open **Settings → Developer Options → Wireless Debugging** and turn it **ON**.
3. Tap **"Pair device with pairing code"** to get the pairing IP, port and 6-digit code.
4. Pair and connect:

   ```bash
   python scripts/connect.py --pair 192.168.1.50:37891 123456
   python scripts/connect.py --connect 192.168.1.50:41235
   ```

Need drivers or troubleshooting? See [`references/connection_guide.md`](references/connection_guide.md).

---

## Usage Guide

A typical session follows **diagnose → audit → optimize → verify**.

### Step 2: Diagnose

#### 1. Find root-cause lag and CPU bottlenecks
```bash
python scripts/diagnose.py
```
Profiles CPU run queues, checks memory pressure and lists the top CPU-burning processes.

#### 2. Audit for sketchy apps and accessibility hijackers
```bash
python scripts/security_audit.py

# Freeze a suspicious app immediately:
python scripts/security_audit.py --quarantine <package_name>
```
Details in [Security and Malware Auditing](#security-and-malware-auditing).

#### 3. Benchmark before and after
```bash
# Baseline BEFORE optimizing:
python scripts/bench.py --app com.android.settings --duration 8 --scroll --save before.json
```
Captures UI frame pacing, jank percentage, P90 latency and 1% Low FPS. After optimizing, repeat with `--save after.json`, then compare:
```bash
python scripts/bench.py --compare before.json after.json
```

### Step 3: Optimize

<details open>
<summary><strong>1. Safe OEM debloating and telemetry elimination</strong></summary>

```bash
# Preview (safe dry run):
python scripts/optimize.py --profile auto --dry-run

# Apply:
python scripts/optimize.py --profile auto
```

| Flag | Description |
| :--- | :--- |
| `--dry-run` | Preview changes without modifying the device |
| `--user <id>` | Target a specific Android user profile (default `0`) |
| `--update-db` | Fetch and merge community-verified debloat entries from UAD-ng |
| `--profile` | `samsung`, `xiaomi`, `realme`, `google` or `auto` |

</details>

<details>
<summary><strong>2. 2x UI animation speedup and cache trimming</strong></summary>

```bash
python scripts/tweak_ui.py --scale 0.5 --trim-cache
```
Halves gesture-navigation latency and trims stale system caches safely.

</details>

<details>
<summary><strong>3. ART ahead-of-time (AOT) pre-compilation</strong></summary>

Pre-compiling hot code paths removes JIT launch stutter.

```bash
# All user apps:
python scripts/compile_speed.py --all-user-apps --filter speed-profile

# One heavy app, maximum performance:
python scripts/compile_speed.py --app com.android.settings --filter speed

# Roll back to default JIT:
python scripts/compile_speed.py --reset-manifest compile_manifest_SM-G615F_YYYYMMDD_HHMMSS.json
python scripts/compile_speed.py --reset-app com.android.settings
```
Every run records a reset manifest in `backups/` and logs to your local device vault (`devices/<slug>/history.md`).

</details>

<details>
<summary><strong>4. AppOps background limits and standby buckets</strong></summary>

For apps you want to keep (Instagram, Facebook, Snapchat, Truecaller, shopping apps) but not have draining CPU or holding wakelocks while minimized:

```bash
# Restrict common social and battery hogs:
python scripts/appops_restrict.py --preset social --bucket restricted

# Restrict one package:
python scripts/appops_restrict.py --app com.instagram.android --mode ignore --bucket restricted

# Preview safely:
python scripts/appops_restrict.py --preset social --dry-run

# Roll back:
python scripts/appops_restrict.py --reset-manifest appops_manifest_SM-G615F_YYYYMMDD_HHMMSS.json
python scripts/appops_restrict.py --reset-app com.instagram.android
```
Each execution captures a pre-flight manifest in `backups/` and logs to your local vault.

</details>

<details>
<summary><strong>5. Disable zRAM / Memory Extension on your phone (manual step)</strong></summary>

Disabling OEM virtual RAM stops `kswapd0` compression thrashing on low-end CPUs. Reboot afterwards.

| OEM | Path |
| :--- | :--- |
| **Xiaomi / HyperOS / MIUI** | Settings → Additional Settings → Memory Extension → **Off** |
| **Samsung One UI** | Settings → Battery and device care → Memory → RAM Plus → **Off** (or 0 GB) |
| **Realme / Oppo / OnePlus** | Settings → About Device → RAM → toggle **RAM Expansion** off |

Background reading: [`references/virtual_ram_guide.md`](references/virtual_ram_guide.md).

</details>

### Step 4: Verify the Speedup

```bash
python scripts/bench.py --app com.android.settings --duration 8 --scroll --save after.json
python scripts/bench.py --compare before.json after.json
```

### Optional Power-User Workflows

<details>
<summary><strong>Run on-device without a PC (Shizuku + Termux)</strong></summary>

Export matched optimization and rollback scripts for your OEM:

```bash
python scripts/export_shizuku.py --profile samsung
# Profiles: samsung, xiaomi, realme, google, social, all
```

Then on the phone:

1. Start Shizuku via Wireless Debugging.
2. In Termux run: `rish apply_optimization_samsung_TIMESTAMP.sh`
3. Roll back on-device: `rish rollback_optimization_samsung_TIMESTAMP.sh`

</details>

<details>
<summary><strong>Sync the community debloat database (UAD-ng)</strong></summary>

Import thousands of peer-reviewed package definitions:

```bash
python scripts/update_database.py                                   # sync from upstream
python scripts/update_database.py --file /path/to/uad_lists.json    # offline import
python scripts/update_database.py --restore-backup package_database_backup_YYYYMMDD_HHMMSS.json
```
Every sync validates package names against an injection regex and writes a pre-flight backup to `backups/package_database_backup_*.json`.

</details>

<details>
<summary><strong>Unified terminal wizard (non-interactive shortcuts)</strong></summary>

```bash
python scripts/wizard.py                          # interactive menu
python scripts/wizard.py --action modes --dry-run
python scripts/wizard.py --action rescue
```

</details>

---

## Security and Malware Auditing

Slow phones are often compromised phones. `security_audit.py` inspects the device entirely over ADB text streams — nothing is executed on your PC.

| Check | What it catches |
| :--- | :--- |
| **Accessibility services** | Apps with screen-reading and click-simulation rights — the primary vector for banking trojans (e.g. TeaBot) and stalkerware |
| **Device administrators** | Unauthorized apps registered with `DevicePolicyManager` that prevent uninstallation |
| **Hidden ghost apps** | Apps running background services with no home-screen launcher icon |
| **Permission clusters** | High-risk combinations such as screen overlay + SMS interception + background location |
| **Quarantine** | `--quarantine <package>` freezes a flagged app in one command |

Deep dive: [`references/malware_and_security.md`](references/malware_and_security.md) · Policy: [`SECURITY.md`](SECURITY.md).

---

## Safety, Rollback and Rescue

ALFi is built so that **nothing it does is a one-way door.**

| Safety layer | How it protects you |
| :--- | :--- |
| **Disable, never delete** | Packages are disabled (`disable-user`), so app data stays intact and apps can be re-enabled at any time |
| **Pre-flight manifest & fsync** | A timestamped JSON snapshot is saved and `os.fsync()`-flushed to `backups/` *before* the first package disable call |
| **On-device manifest mirror** | A copy is written to `/sdcard/.lagfixer_manifest.json` so you can restore via Shizuku (`rish`) with no PC |
| **Strict allowlist** | OTA updaters, Google Play Services, WebView, telephony / emergency dialers, OEM account logins, banking apps and Widevine L1 are never touched |
| **Dependency graph** | Disabling is blocked if an installed app depends on the target (e.g. Samsung Account → Galaxy Wearable / Galaxy Store) |
| **State verification** | Results are confirmed through `pm list packages -e/-d/-u` and `dumpsys package`, with a fallback ladder |
| **Dry-run everywhere** | Add `--dry-run` to preview any operation |

### 1-Click Rollback

```bash
python scripts/restore.py --manifest latest --dry-run   # preview
python scripts/restore.py --manifest latest             # restore latest session
python scripts/restore.py --package com.example.app     # restore one package
```

### Emergency Feature Rescue

If the dialer, Play Services, Settings, Camera, SystemUI, Keyguard or WebView misbehaves:

```bash
# 1. Revive any disabled critical core components:
python scripts/rescue.py --fix-critical

# 2. Deep multi-layer rescue for one package (enable, reinstall, reset AppOps, bucket and ART):
python scripts/rescue.py --rescue-package com.google.android.dialer

# 3. Re-enable every disabled package in the user profile:
python scripts/rescue.py --restore-all-disabled

# 4. List all reset points and backup manifests:
python scripts/rescue.py --list-manifests

# 5. Hardware Safe Mode / bootloop key combinations for your OEM:
python scripts/rescue.py --guide samsung    # samsung, xiaomi, google, realme_oneplus, general
```
Each rescue captures a snapshot in `backups/rescue_snapshot_*.json` and logs to your local device vault.

### Multi-Device Audit Tracker

Manage family phones or client devices without name collisions:

```bash
python scripts/device_tracker.py --status   # current device and its history
python scripts/device_tracker.py --list     # all tracked devices
```
> `devices/` and `backups/` hold your private hardware serials and snapshots. They are **gitignored automatically**.

---

## Under the Hood: Advanced Engines

ALFi borrows proven ideas from the best open-source Android tooling.

<details>
<summary><strong>🧩 Package dependency graph engine</strong> <em>(inspired by UAD-ng)</em></summary>

**Problem:** blindly disabling vendor packages breaks dependents — e.g. disabling Samsung Account breaks Galaxy Wearable and Galaxy Store; disabling Google Services Framework breaks Google Play.

**Solution:** `package_database.json` stores explicit `dependencies` and `dependents`. Before disabling anything, the resolver checks whether dependent apps are installed; if one is active the action is **strictly blocked** with an actionable warning. Core OS services (keyboards, launchers, WebViews, telephony) are hard-whitelisted.

</details>

<details>
<summary><strong>📱 Persistent on-device manifests</strong> <em>(inspired by Canta)</em></summary>

**Problem:** if something breaks while you travel without a PC, desktop ADB restore manifests are out of reach.

**Solution:** alongside `backups/` on your PC, ALFi mirrors a snapshot to `/sdcard/.lagfixer_manifest.json` on the phone, enabling fully rootless on-device restoration through Shizuku (`rish`).

</details>

<details>
<summary><strong>🔋 Deep Doze enforcement and allowlist auditor</strong> (<code>scripts/doze_boost.py</code>) <em>(inspired by Android DeviceIdle and Brevent)</em></summary>

**Problem:** rogue third-party apps and OEM bloat add themselves to the battery-optimization whitelist (`dumpsys deviceidle whitelist`), bypassing Doze and draining battery with the screen off.

**Solution:** audits the Doze allowlist, strips rogue pollers via `cmd deviceidle whitelist -<pkg>`, and triggers rapid Deep Doze on screen-off (`cmd deviceidle force-idle`). Includes 1-click snapshot restore.

</details>

<details>
<summary><strong>⚡ Empirical battery drain and wakelock proof</strong> (<code>scripts/power_audit.py</code>) <em>(inspired by Google BatteryStats and Battery Historian)</em></summary>

**Problem:** users want proof that background optimizations actually save battery.

**Solution:** parses `dumpsys batterystats` to quantify partial wakelocks, CPU wakeups and drain in mAh/hr, with a before-vs-after mode:

```text
======================================================================
 ⚡ EMPIRICAL BATTERY & WAKELOCK REDUCTION AUDIT (BEFORE vs AFTER)
======================================================================
 Metric                    | Before       | After        | Savings
----------------------------------------------------------------------
 Partial Wakelocks         | 142          | 18           | -87.3%
 Wakelock Active (ms)      | 930000       | 120000       | -87.1%
 Drain Rate (mAh/hr)       | 38.0         | 12.0         | -68.4%
======================================================================
```

</details>

<details>
<summary><strong>🖥️ Real-time screen mirroring bridge</strong> <em>(inspired by scrcpy)</em></summary>

**Problem:** judging touch responsiveness means glancing between monitor and handset.

**Solution:** the wizard auto-detects a local `scrcpy` install and offers a 1-click launcher (`[S] 📱 Launch Real-Time Screen Mirror`) so you can mirror and control the phone from your desktop.

</details>

---

## Compatibility

### Supported Android Versions

| Android | Status |
| :--- | :--- |
| **9 – 16** | Supported |
| **17+ (SDK 37+)** | Supported — automatic fallback to `disable-user` where user-space system uninstalls are blocked |
| **8.1** | Validated on a Samsung Galaxy J7 Max (see [benchmarks](#device-2--legacy-samsung-phone)) |

### Supported OEMs and Profiles

| OEM / ROM | What ALFi targets |
| :--- | :--- |
| **Samsung (One UI)** | McAfee Device Security, Game Launcher ads, Bixby telemetry, RAM Plus |
| **Xiaomi (MIUI and HyperOS)** | MIUI System Ads (MSA), Analytics daemon, Wallpaper Carousel / Glance lockscreen ads, Joyose throttling, App Mall pushers |
| **Realme / Oppo / OnePlus (ColorOS / OxygenOS)** | HeyTap notification wakelocks, ColorOS telemetry (`com.oplus.statistics.rom`), DeepThinker tracking, Oplus commercial ads |
| **Google Pixel / stock Android** | Safe baseline profile |
| **Universal social bloat** | Pre-installed Meta / Facebook daemons (`com.facebook.system`, `com.facebook.appmanager`, `com.facebook.services`, `com.facebook.katana`) |
| **Always protected** | Google Play Services, Android System WebView, OTA updaters, telephony / emergency dialers, banking apps |

Full catalogs: [`references/oem_catalogs.md`](references/oem_catalogs.md) · [`references/safety_matrix.md`](references/safety_matrix.md).

---

## How ALFi Compares

| | **ALFi** | Cleaner / booster apps | Rooted tweaks | Factory reset |
| :--- | :---: | :---: | :---: | :---: |
| No root required | ✅ | ✅ | ❌ | ✅ |
| Reversible in one command | ✅ | ❌ | ⚠️ varies | ❌ |
| Preserves app data | ✅ | ⚠️ varies | ⚠️ varies | ❌ |
| Measures real before/after results | ✅ | ❌ | ❌ | ❌ |
| Audits for trojans and stalkerware | ✅ | ⚠️ varies | ❌ | ❌ |
| Runs untrusted binaries on your PC | **Never** | n/a | n/a | n/a |
| Zero external pip dependencies | ✅ (100% stdlib) | ❌ | ❌ | n/a |
| Protects OTA, banking and Widevine L1 | ✅ | ❌ | ❌ | ✅ |

ALFi is inspired by tools like [UAD-ng](https://github.com/Universal-Debloater-Alliance/universal-android-debloater-next-generation), Canta and scrcpy, and adds diagnostics, benchmarking, security auditing and tiered optimization modes on top of debloating.

---

## FAQ

<details>
<summary><strong>Do I need to root my phone to use ALFi?</strong></summary>

No. ALFi uses standard, non-root ADB commands only. Because it avoids rooting, it avoids the side effects rooting is known for, such as tripping Knox or losing Widevine L1, and its allowlist specifically protects banking apps and Widevine L1 DRM.

</details>

<details>
<summary><strong>Is it safe? Can I undo what ALFi did?</strong></summary>

Yes. ALFi *disables* packages rather than uninstalling them, so app data is preserved. Every operation saves and `fsync`s a timestamped manifest before making changes, and `python scripts/restore.py --manifest latest` reverses your last session. For anything unexpected, `python scripts/rescue.py --fix-critical` revives disabled core components.

</details>

<details>
<summary><strong>How do I fix lag on my Android phone without a factory reset?</strong></summary>

Run `alfi`, diagnose with `diagnose.py`, then apply the **Medium** mode. This removes background telemetry and adware, reduces memory pressure, and speeds up animations. Then confirm the gain with `bench.py --compare`.

</details>

<details>
<summary><strong>Should I turn off RAM Plus / Memory Extension / RAM Expansion?</strong></summary>

On budget and older phones with weak CPU clusters, often yes. Compressing memory into zRAM costs CPU time, and `kswapd0` can compete with the UI thread. ALFi's **High** and **Ultra** modes include guidance for disabling it; use `diagnose.py` to see whether your phone is under swap pressure first.

</details>

<details>
<summary><strong>How do I remove bloatware over ADB without root?</strong></summary>

Run `python scripts/optimize.py --profile auto --dry-run` to preview, then drop `--dry-run` to apply. ALFi detects your OEM, checks the dependency graph and allowlist, and writes a restore manifest.

</details>

<details>
<summary><strong>Can ALFi detect banking trojans, stalkerware or hidden adware?</strong></summary>

`security_audit.py` flags apps abusing Accessibility Services, unauthorized Device Administrators, launcher-less ghost apps and dangerous permission combinations, and can quarantine them. It is an auditing aid, not a replacement for a full antivirus.

</details>

<details>
<summary><strong>Does ALFi work wirelessly?</strong></summary>

Yes. On Android 11+, use Wireless Debugging and `python scripts/connect.py --pair <ip:port> <code>`.

</details>

<details>
<summary><strong>Can I run it without a PC?</strong></summary>

Yes, using Shizuku and Termux. Generate scripts with `export_shizuku.py` and run them with `rish`. The on-device manifest mirror enables rollback too.

</details>

<details>
<summary><strong>Does ALFi store or upload my device data?</strong></summary>

Audit history, serials and snapshots are kept locally in `devices/` and `backups/`, which are gitignored by default. Scans run through standard ADB shell commands, and ALFi never executes Android binaries on your computer.

</details>

<details>
<summary><strong>Which Android versions are supported?</strong></summary>

Android 9 through 17+, and it has also been validated on Android 8.1. Android 17's block on user-space system uninstalls is handled automatically.

</details>

---

## Repository Structure

<details>
<summary><strong>Show full project tree</strong></summary>

```text
alfi/
├── .github/workflows/ci.yml                 # Multi-OS GitHub Actions CI (Ubuntu, Windows, macOS across Python 3.10-3.13)
├── pyproject.toml                           # Modern PEP 517/621 packaging with global CLI entry points
├── LICENSE                                  # MIT Open Source License
├── README.md                                # Comprehensive user & developer guide
├── SKILL.md                                 # Agent Skill specification (Antigravity/Claude)
├── CONTRIBUTING.md                          # Contribution guidelines & fixture reporting
├── SECURITY.md                              # Security policy & isolation guarantees
├── package_database.json                    # Multi-tier risk catalog (Recommended, Advanced, Unsafe)
│
├── scripts/
│   ├── __init__.py                          # Package root & metadata
│   ├── connect.py                           # Device connection & wireless pairing wizard
│   ├── diagnose.py                          # CPU load, ZRAM, memory pressure & process auditor
│   ├── modes.py                             # 4-tier optimization engine & package dependency graph
│   ├── doze_boost.py                        # Deep Doze controller & deviceidle allowlist auditor
│   ├── power_audit.py                       # Empirical batterystats wakelock & mAh drain analyzer
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
│   ├── errors.py                            # Actionable error taxonomy & remediation engine
│   ├── tweak_ui.py                          # 2x animation scaling & system cache trimmer
│   └── device_tracker.py                    # Hardware serial fingerprinting & multi-device audit vault
│
├── tests/
│   ├── fixtures/                            # Real recorded device dumps (Samsung, Redmi, Pixel, Android 17)
│   ├── test_diagnose.py                     # Mocked tests for CPU loadavg & zRAM swap diagnostics
│   ├── test_restore.py                      # Mocked tests for manifest discovery & rollbacks
│   ├── test_security_audit.py               # Mocked tests for 3rd-party installers & accessibility
│   ├── test_modes.py                        # Mocked tests for 4 optimization modes & dependency safety
│   ├── test_doze_boost.py                   # Mocked tests for Doze allowlist parsing & force-idle
│   ├── test_power_audit.py                  # Mocked tests for batterystats parsing & comparison engine
│   ├── test_operations.py                   # Automated unit tests for package mutations
│   ├── test_compile_speed.py                # Mocked tests for ART compilation & reset points
│   ├── test_appops_restrict.py              # Mocked tests for AppOps limits & standby buckets
│   ├── test_rescue.py                       # Mocked tests for emergency feature rescue & recovery
│   ├── test_export_shizuku.py               # Mocked tests for Shizuku & rollback shell exporter
│   ├── test_update_database.py              # Mocked tests for community list parsing & database merging
│   ├── test_wizard.py                       # Mocked tests for terminal wizard, device manager & scrcpy
│   └── test_oem_fixtures.py                 # Mock hardware integration tests against OEM fixtures
│
└── references/
    ├── connection_guide.md                  # USB drivers, developer settings, wireless debugging
    ├── malware_and_security.md              # Technical breakdown of accessibility trojans & adware
    ├── virtual_ram_guide.md                 # zRAM CPU overhead and memory extension analysis
    ├── oem_catalogs.md                      # Samsung, Xiaomi, Realme, OnePlus bloat catalogs
    └── safety_matrix.md                     # Whitelist rules for 100% OTA, Banking & Account integrity
```

</details>

---

## Contributing, Security and License

- **Contribute:** verified OEM package reports and benchmark results are very welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).
- **Report a vulnerability:** see [SECURITY.md](SECURITY.md).
- **License:** [MIT](LICENSE) — free for personal and commercial use.

If ALFi fixed your phone, a ⭐ on the repo helps other people with laggy Android devices find it.

---

<sub>**Keywords:** android lag fix, fix slow android phone, android debloater without root, adb debloat, remove bloatware adb, disable zram, disable ram plus, memory extension off, samsung one ui debloat, xiaomi hyperos debloat, miui debloat, realme coloros debloat, android performance optimizer, android security audit, accessibility service malware detector, android stalkerware detection, adb shell optimization, android jank benchmark, gfxinfo framestats, android doze optimization, shizuku rish scripts, universal android debloater alternative.</sub>
