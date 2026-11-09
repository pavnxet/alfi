# Safety Classification & Critical System Whitelist

This document establishes the safety guardrails, mode boundaries, and dependency verification matrix enforced by **ALFi — Android Lag Fixer** to ensure zero disruption to official software updates (OTA), banking apps, security credentials, input methods, home screens, and cloud backups.

---

## 1. The 4-Tier Mode Risk Boundaries

Instead of treating all optimizations equally, the toolkit groups all modifications into 4 distinct, calibrated tiers:

| Mode | Risk Level | Boundary & Scope | Safety Gate Enforced |
|---|---|---|---|
| **`🟢 Low`** | **Zero Risk** | Carrier stubs, adware preloads, system cache trim, gentle 0.75x animation scales. Untouched OEM services and user apps. | Automatic 1-click execution. |
| **`🟡 Medium`** | **Low Risk (Daily Driver)** | Low + OEM telemetry & tracking daemons, 0.5x animations, ART `speed-profile` compilation, social AppOps background limits. | Automatic 1-click execution. |
| **`🟠 High`** | **Moderate Risk** | Medium + advanced vendor features (Bixby, AR Emoji, Joyose), App Standby `restricted`, Deep Doze allowlist cleanup, Virtual RAM off guidance. | Pre-flight manifest snapshot + summary preview. |
| **`🔴 Ultra`** | **High Risk (Probable Breaking)** | High + duplicate OEM accounts (Samsung/Mi ID), duplicate app stores, secondary keyboards/launchers, 0.0x zero animations, full system ART `speed` compilation. | **Double Gate**: Mandatory dependency graph check + user must type `I UNDERSTAND`. |

---

## 2. Package Dependency Conflict Matrix *(Inspired by UAD-ng)*

Disabling an upstream service without disabling downstream apps causes crashes or broken workflows. The toolkit checks for installed dependents before allowing an operation:

| Package | Role | Dependents (Apps Requiring This) | Rule |
|---|---|---|---|
| `com.osp.app.signin` | Samsung Account | `com.sec.android.app.samsungapps` (Galaxy Store)<br>`com.samsung.android.app.watchmanager` (Galaxy Wearable) | **BLOCKED** if Galaxy Store or Galaxy Watch is installed. Allowed only in Ultra mode if dependents are also disabled. |
| `com.xiaomi.account` | Xiaomi Mi Account | `com.xiaomi.discover` (GetApps Store)<br>`com.miui.cloudservice` (Mi Cloud) | **BLOCKED** if GetApps or Mi Cloud is active. |
| `com.oplus.account` | HeyTap / Realme Account | `com.heytap.market` (App Market)<br>`com.heytap.usercenter` (User Center) | **BLOCKED** if HeyTap Market is active. |
| `com.google.android.gms` | Google Play Services | All Google apps, Push notifications, SafetyNet/Play Integrity | **HARD BLOCKED (Never Touched)** across all modes. |

---

## 3. Hard Whitelist (Packages That Are NEVER Touched)

### A. Critical System Subsystems (OS Crash Prevention)
- `com.android.phone`: Cellular radio, SIM management, emergency 911/112 dialer.
- `com.android.systemui`: Status bar, navigation bar, lockscreen compositor.
- `com.android.settings`: System Settings preferences provider.
- `com.google.android.webview` / `com.google.android.trichromelibrary`: Shared WebView renderer for banking & browser apps.
- `com.android.packageinstaller`: Core APK installation service.

### B. Input Method & Keyboard Safeguard
- `com.google.android.inputmethod.latin` (Gboard)
- `com.samsung.android.honeyboard` (Samsung Keyboard)
- `com.touchtype.swiftkey` (SwiftKey)
> **Safety Rule**: Disabling a keyboard is **strictly blocked** if no other active keyboard remains installed on the device.

### C. Home Screen & Launcher Safeguard
- `com.sec.android.app.launcher` (One UI Home)
- `com.miui.home` (MIUI / HyperOS Launcher)
- `com.google.android.apps.nexuslauncher` (Pixel Launcher)
- `com.android.launcher3` (AOSP Launcher)
> **Safety Rule**: Disabling a system launcher is **strictly blocked** unless a verified third-party launcher (e.g. Nova Launcher) is confirmed installed and active.

### D. System Software Updates (OTA Integrity)
Disabling OTA engines blocks security patches and Android version upgrades. The following packages are strictly protected:
- `com.oplus.ota` (Realme / ColorOS OTA engine)
- `com.oplus.romupdate` (Security patch delta verifier)
- `com.google.android.configupdater` (Google Play System & Mainline updater)
- `com.wssyncmldm` (Samsung firmware update client)
- `com.android.updater` (Xiaomi HyperOS / MIUI updater)

---

## 4. The Non-Destructive Guarantee (`pm disable-user`)

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

## 5. Version-Aware Command Resolution & Data Retention (Android 6 to 17+)

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
