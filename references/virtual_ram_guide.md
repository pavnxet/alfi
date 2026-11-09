# Virtual RAM & zRAM: The Real Cost of Memory Extension on Android

## 1. What is Virtual RAM / Memory Extension?

Marketed under various OEM trade names:
- **Samsung**: *RAM Plus*
- **Realme / Oppo / OnePlus (ColorOS)**: *RAM Expansion*
- **Xiaomi / Redmi / Poco (HyperOS / MIUI)**: *Memory Extension*
- **Motorola / Vivo**: *RAM Boost / Extended RAM*

OEMs claim this feature adds 2 GB to 12 GB of extra RAM to your device. 

### The Architecture: It's zRAM, Not Storage Swap
Contrary to popular myth, Android does not create traditional storage-backed swap files on flash storage for app paging. Instead, OEM memory expansion configures a larger **zRAM block device**—a compressed memory pool allocated entirely *inside physical RAM*.

When physical memory runs low, the Linux kernel compresses inactive memory pages using lightweight algorithms (LZ4, ZSTD) and stores them in this reserved zRAM slice.

---

## 2. Why Memory Extension Causes UI Stutters & Jank

While zRAM is essential for keeping budget devices functional, **oversizing the zRAM pool via "Memory Extension" has severe drawbacks on mid-range and budget processors**:

### A. Heavy CPU Compression Cycles on Weak Cores
- Every page moved into or out of zRAM requires active CPU compression and decompression.
- On budget processors (Cortex-A53 / Cortex-A55 clusters), continuous LZ4/ZSTD compression spikes CPU utilization in `kswapd0`.
- When app switching or scrolling, the main UI thread competes with `kswapd0` for CPU time slices, causing **dropped frames, jank, and micro-stutters**.

### B. High Context-Switch Overhead & Memory Thrashing
- When virtual RAM is set too high (e.g., 6 GB or 8 GB on a 4 GB device), the kernel aggressively attempts to keep dozens of stale apps compressed in RAM rather than killing them cleanly via low-memory-killer (`lmkd`).
- The constant page-fault and swap-in cycles produce noticeable touch latency and thermal heating.

### C. Flash Storage Space Reservation
- While zRAM compresses inside RAM, OEMs often reserve internal flash blocks as an emergency backing store or reservation table, reducing user-available storage.

---

## 3. Best Practice Recommendation: When to Turn it Off

| Device RAM Size | Recommendation | Rationale |
|---|---|---|
| **2 GB – 3 GB** | Keep **2 GB** enabled | Essential to prevent aggressive out-of-memory app crashes (`lmkd`). |
| **4 GB – 6 GB** | **Turn OFF** or set to **1–2 GB** | Eliminates CPU compression jank during multitasking. |
| **8 GB – 12 GB+** | **Turn OFF (0 GB)** | Physical RAM is already plenty; extra zRAM only wastes CPU cycles and battery. |

---

## 4. How to Disable or Tune Virtual RAM

### Samsung (One UI)
If One UI does not expose a 0 GB / Off option, run:
```bash
adb shell settings put global ram_expand_size_list 0,1,2,4,6,8
```
Then go to **Settings > Battery and device care > Memory > RAM Plus** and select **0 GB** (or toggle **Off** on One UI 5+), then restart.

### Xiaomi / HyperOS / MIUI
Go to **Settings > Additional Settings > Memory Extension** > select **Off**, then restart.

### Realme / Oppo / OnePlus (ColorOS)
Go to **Settings > About Device > RAM** > toggle **OFF 'RAM Expansion'**, then restart.
