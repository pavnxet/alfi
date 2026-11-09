# Safety Classification & Critical System Whitelist

This document establishes the safety guardrails enforced by **Phone Lag Fixer** to ensure zero disruption to official software updates (OTA), banking apps, security credentials, and cloud backups.

---

## 1. Multi-Tier Risk Classification

Inspired by the Universal Android Debloater (UAD-ng) taxonomy:

| Tier | Definition | Examples | Default Action |
|---|---|---|---|
| **`Recommended`** | 100% safe to disable. Bloatware, advertising frameworks, third-party pre-installs, and telemetry daemons. Zero negative impact on daily device usage. | `com.oplus.statistics.rom`, `com.facebook.system`, `com.miui.msa.global`, `com.microsoft.appmanager` | **Disabled automatically** |
| **`Advanced`** | Safe to disable unless you actively use that specific vendor service. | `com.heytap.mcs` (HeyTap Cloud push), `com.samsung.android.bixby.agent`, `com.samsung.android.aremoji` | **Prompted / Optional** |
| **`Expert`** | Safe only for power users who intentionally replace standard system workflows. | Printing spooler, live wallpaper picker, stock gallery | **Skipped by default** |
| **`Unsafe` (Whitelisted)** | **CRITICAL SUBSYSTEMS.** Disabling these may result in bootloops, inability to make phone calls, loss of banking access, or broken OTA updates. | System UI, Telephony, Account sign-in, OTA Update clients | **HARD BLOCKED (Never touched)** |

---

## 2. Hard Whitelist (Packages That Are NEVER Touched)

### A. System Software Updates (OTA Integrity)
Disabling OTA engines blocks security patches and Android version upgrades. The following packages are strictly protected:
- `com.oplus.ota` (Realme / ColorOS OTA engine)
- `com.oplus.romupdate` (Security patch delta verifier)
- `com.oplus.cota` (Carrier operator OTA configuration)
- `com.google.android.configupdater` (Google Play System & Mainline updater)
- `com.wssyncmldm` (Samsung firmware update client)
- `com.android.updater` (Xiaomi HyperOS / MIUI updater)

### B. User Accounts, Cloud Sync & 2FA
To guarantee seamless access to saved contacts, gallery backups, and 2-factor authentication prompts:
- `com.oplus.account` & `com.heytap.usercenter` (Realme / Oppo ID login)
- `com.heytap.cloud` (HeyTap Cloud backup)
- `com.osp.app.signin` (Samsung Account authentication)
- `com.google.android.gms` (Google Play Services)

### C. Security, Banking & DRM
- `com.google.android.webview` (Required for displaying in-app banking & browser logins)
- `com.android.keyguard` (PIN, password, and biometric fingerprint/face authentication)
- Widevine L1 DRM libraries (Preserves Full HD streaming in Netflix, Prime Video, etc.)

---

## 3. The Non-Destructive Guarantee (`pm disable-user`)

Traditional root scripts delete `.apk` files directly from `/system/app`, which breaks dm-verity and bricks phones upon reboot.

This toolkit strictly employs user-space package states:
```bash
adb shell pm disable-user --user 0 <package_name>
```

**Why this is 100% disaster-free**:
1. The read-only `/system` and `/vendor` partitions are **never modified**.
2. dm-verity and Android Verified Boot (AVB) remain completely intact.
3. The app is immediately killed in RAM, stripped of boot receivers, and prevented from launching.
4. Any package can be instantly reinstated with zero data loss using:
   ```bash
   adb shell pm enable <package_name>
   ```
5. A factory reset automatically restores 100% of out-of-the-box factory settings.

---

## 4. Version-Aware Command Resolution & Data Retention (Android 6 to 17+)

| Desired State | Current State | Android 6–16 Execution | Android 17+ (SDK 37+) Resolution | Data Retention |
|---|---|---|---|---|
| **Disabled** | Enabled | `pm disable-user --user <id>` | `pm disable-user --user <id>` | **100% Preserved** (App data & preferences intact) |
| **Uninstalled** | Enabled | `pm uninstall --user <id>` | **Blocked by platform ➡️ Falls back to `disable-user`** | App data deleted (APK preserved in `/system`) |
| **Enabled** | Disabled | `pm enable --user <id>` | `pm enable --user <id>` | **100% Preserved** |
| **Reinstalled** | Uninstalled | `cmd package install-existing --user <id>` | `cmd package install-existing --user <id>` | Fresh out-of-the-box app data |

### Fallback Ladder
If OEM restrictions block a command:
- `uninstall ➡️ disable`: When `only root can delete` or `DELETE_FAILED_USER_RESTRICTED` is returned.
- `disable ➡️ uninstall`: When `Cannot disable system packages` (HyperOS / MIUI SecurityException) is returned.

