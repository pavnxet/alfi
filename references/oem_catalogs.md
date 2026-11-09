# Multi-OEM Bloatware, Telemetry & Adware Reference Catalog

This reference document catalogs common pre-installed system packages across major Android OEMs, detailing their technical responsibilities, resource footprint, and debloating recommendations.

---

## 1. Samsung Galaxy (One UI / Experience)

| Package Name | Service Name | Default Tier | Technical Impact & Resource Usage |
|---|---|---|---|
| `com.samsung.android.sm.devicesecurity` | McAfee Device Security | `Recommended` | Consistently drains **10-15% CPU** in background while performing periodic storage scanning. High thermal impact. |
| `com.samsung.android.spaymini` | Samsung Pay Mini | `Recommended` | Persistent background payment framework and promotion daemon. |
| `com.samsung.android.game.gamehome` | Game Launcher | `Recommended` | Delivers sponsored game ads, notifications, and telemetry. |
| `com.samsung.android.game.gametools` | Game Tools | `Recommended` | Floating window overlay hooks consuming compositor resources. |
| `com.samsung.android.voc` | Samsung Members | `Recommended` | Automated diagnostic log collection and community telemetry. |
| `com.samsung.android.aremoji` | AR Emoji Assets | `Advanced` | Consumes ~120 MB storage and background camera services. Safe to disable if unused. |
| `com.samsung.android.bixby.agent` | Bixby Voice Agent | `Advanced` | Persistent wake-word listener and background audio processing wakelocks. |

---

## 2. Realme / Oppo / OnePlus (ColorOS / Realme UI)

| Package Name | Service Name | Default Tier | Technical Impact & Resource Usage |
|---|---|---|---|
| `com.microsoft.appmanager` | Link to Windows | `Recommended` | Infamous loop bug consuming **>100% CPU** continuously when disconnected. |
| `com.oplus.statistics.rom` | Usage Analytics | `Recommended` | Runs `HalfHourTimerJobService` to harvest and upload diagnostic telemetry (~122 MB RAM). |
| `com.oplus.onetrace` | Systrace Profiler | `Recommended` | Kernel-level performance logging consuming ~117 MB RAM. |
| `com.oplus.deepthinker` | AI Habit Prediction | `Recommended` | Intercepts app switches and gestures to train predictive models (~112 MB RAM). |
| `com.oplus.commercial` | Ad Delivery System | `Recommended` | Background engine for recommended apps and banner ads in system folders. |
| `com.oplus.crashbox` | Crashbox Log Collector | `Recommended` | Continuous log file writes to flash storage. |
| `com.heytap.mcs` | HeyTap Push Service | `Advanced` | Generates 100+ wakeups every 5 minutes (disable if HeyTap Cloud is not used). |

---

## 3. Xiaomi / Redmi / POCO (HyperOS / MIUI)

| Package Name | Service Name | Default Tier | Technical Impact & Resource Usage |
|---|---|---|---|
| `com.miui.msa.global` | MIUI System Ads (MSA) | `Recommended` | Central advertising daemon pushing banners and lockscreen promotions. |
| `com.miui.analytics` | MIUI Analytics | `Recommended` | Collects comprehensive behavioral analytics and device usage logs. |
| `com.xiaomi.joyose` | Joyose Throttler | `Recommended` | Known for aggressive thermal down-throttling in games and benchmark throttling. |
| `com.miui.daemon` | System Daemon | `Recommended` | Periodic log collector and diagnostic telemetric reporter. |
| `com.miui.cleanmaster` | CleanMaster Engine | `Recommended` | Bundled Cheetah Mobile cleaner engine laden with ad network SDKs. |
| `com.miui.hybrid` | Quick Apps Framework | `Recommended` | Engine for running instant cloud mini-apps and promotional webviews. |

---

## 4. Universal Social & Third-Party Bloat

| Package Name | Service Name | Default Tier | Technical Impact & Resource Usage |
|---|---|---|---|
| `com.facebook.katana` | Facebook Stub | `Recommended` | System pre-install that cannot be uninstalled normally from Play Store. |
| `com.facebook.system` | FB App Installer | `Recommended` | Silent background app installer bypassing Google Play Store. |
| `com.facebook.appmanager` | FB App Manager | `Recommended` | Background service tracking application analytics. |
| `com.facebook.services` | Facebook Services | `Recommended` | Telemetry and device fingerprinting daemon. |
