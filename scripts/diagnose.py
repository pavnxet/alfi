#!/usr/bin/env python3
"""
scripts/diagnose.py - Deep Performance & Lag Diagnostic Engine

Analyzes CPU load, memory/ZRAM pressure, Virtual RAM thrashing, storage I/O wait,
and detects rogue background hogs without modifying any device state.
"""

import sys
import re

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from connect import find_adb, run_adb, get_connected_devices, get_device_info

def check_cpu_and_load(serial=None):
    """Retrieve load average and top CPU consumers."""
    prefix = ["-s", serial] if serial else []
    
    # 1. Load averages
    ok, load_out = run_adb(prefix + ["shell", "cat /proc/loadavg"])
    load_avg = load_out.split()[:3] if ok else ["Unknown", "Unknown", "Unknown"]
    
    # 2. Dumpsys cpuinfo (past few seconds)
    ok, cpu_out = run_adb(prefix + ["shell", "dumpsys cpuinfo"], timeout=15)
    
    top_procs = []
    total_cpu_line = ""
    if ok:
        lines = cpu_out.splitlines()
        for line in lines:
            line_str = line.strip()
            if "TOTAL:" in line_str:
                total_cpu_line = line_str
            # Match lines like "15% 1234/com.example: 10% user + 5% kernel"
            match = re.search(r"(\d+(?:\.\d+)?%)\s+(\d+)/([^:]+):", line_str)
            if match and len(top_procs) < 8:
                top_procs.append({
                    "pct": match.group(1),
                    "pid": match.group(2),
                    "name": match.group(3).strip()
                })
                
    return load_avg, total_cpu_line, top_procs

def check_memory_and_swap(serial=None):
    """Analyze RAM, ZRAM swap usage, and flash thrashing indicators."""
    prefix = ["-s", serial] if serial else []
    
    ok, mem_out = run_adb(prefix + ["shell", "cat /proc/meminfo"])
    mem_stats = {}
    if ok:
        for line in mem_out.splitlines():
            parts = line.split(":")
            if len(parts) == 2:
                key = parts[0].strip()
                val_parts = parts[1].strip().split()
                if val_parts:
                    try:
                        mem_stats[key] = int(val_parts[0]) # in kB
                    except ValueError:
                        pass

    total_ram = mem_stats.get("MemTotal", 0) / 1024 # MB
    avail_ram = mem_stats.get("MemAvailable", 0) / 1024 # MB
    swap_total = mem_stats.get("SwapTotal", 0) / 1024 # MB
    swap_free = mem_stats.get("SwapFree", 0) / 1024 # MB
    swap_used = swap_total - swap_free

    # Check for flash GC or storage wait
    ok, ps_out = run_adb(prefix + ["shell", "ps -A | grep -E 'f2fs_gc|kswapd'"])
    vram_thrashing = False
    gc_status = "Inactive / Sleep"
    if ok and "f2fs_gc" in ps_out:
        # Check if D state (disk sleep) or consuming CPU
        if " D " in ps_out or " R " in ps_out:
            vram_thrashing = True
            gc_status = "ACTIVE / THRASHING (F2FS Storage I/O lock detected)"
        else:
            gc_status = "Present (Sleeping)"

    return {
        "total_ram_mb": round(total_ram, 1),
        "avail_ram_mb": round(avail_ram, 1),
        "swap_total_mb": round(swap_total, 1),
        "swap_used_mb": round(swap_used, 1),
        "vram_thrashing": vram_thrashing,
        "gc_status": gc_status
    }

def check_animation_scales(serial=None):
    """Inspect window and transition animation duration scales."""
    prefix = ["-s", serial] if serial else []
    scales = {}
    keys = ["window_animation_scale", "transition_animation_scale", "animator_duration_scale"]
    for k in keys:
        ok, val = run_adb(prefix + ["shell", f"settings get global {k}"])
        scales[k] = val if ok and val else "1.0 (default)"
    return scales

def check_known_cpu_burners(serial=None):
    """Check if infamous performance-killing packages are actively running."""
    prefix = ["-s", serial] if serial else []
    known_burners = [
        ("com.microsoft.appmanager", "Microsoft Link to Windows", "Known 131% CPU infinite loop bug"),
        ("com.samsung.android.sm.devicesecurity", "McAfee Device Security", "Constant background virus scanning hogging 10-15% CPU"),
        ("com.arlosoft.macrodroid", "MacroDroid", "Heavy window accessibility hooks causing compositor page faults"),
        ("com.heytap.mcs", "HeyTap Push Notification", "Excessive wakelocks preventing CPU deep sleep")
    ]
    
    findings = []
    for pkg, name, note in known_burners:
        ok, out = run_adb(prefix + ["shell", f"pidof {pkg}"])
        if ok and out:
            findings.append({"pkg": pkg, "name": name, "pids": out, "note": note})
            
    return findings

def main():
    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    if not auth:
        print("❌ No authorized Android device connected. Run 'python scripts/connect.py' first.")
        sys.exit(1)

    target_serial = auth[0]["serial"]
    info = get_device_info(target_serial)
    
    print("\n" + "="*65)
    print(f" 🔍 RUNNING PERFORMANCE AUDIT ON: {info['brand'].upper()} {info['model']}")
    print("="*65)

    # 1. CPU & Load
    print("[*] Profiling CPU load averages & process run queues...")
    load_avg, total_cpu, top_procs = check_cpu_and_load(target_serial)
    print(f"\n  • CPU Load Average (1m, 5m, 15m) : {load_avg[0]} / {load_avg[1]} / {load_avg[2]}")
    try:
        one_min_load = float(load_avg[0])
        if one_min_load > 10.0:
            print("    ⚠️ SEVERE CPU CONGESTION: Load is >10.0 (normal idle is <2.0). Heavy throttling expected.")
        elif one_min_load > 4.0:
            print("    ⚠️ MODERATE CPU LOAD: Multi-core system under noticeable stress.")
        else:
            print("    ✅ CPU Load is healthy and within normal baseline.")
    except ValueError:
        pass

    if total_cpu:
        print(f"  • {total_cpu}")

    if top_procs:
        print("\n  • Top CPU Consuming Processes:")
        for p in top_procs:
            print(f"    - {p['pct']:>6} CPU | PID {p['pid']:>5} | {p['name']}")

    # 2. Memory & Virtual RAM Thrashing
    print("\n[*] Analyzing physical memory, ZRAM swap, and Flash I/O locks...")
    mem = check_memory_and_swap(target_serial)
    print(f"  • Physical RAM     : {mem['avail_ram_mb']} MB available / {mem['total_ram_mb']} MB total")
    print(f"  • ZRAM / Swap      : {mem['swap_used_mb']} MB used / {mem['swap_total_mb']} MB total")
    print(f"  • Flash Garbage Collector: {mem['gc_status']}")

    if mem["vram_thrashing"]:
        print("    🚨 WARNING: Virtual RAM / RAM Expansion is thrashing your UFS/eMMC flash storage!")
        print("    This causes 1-2 second UI freezes, app launch stutters, and accelerates flash memory wear.")
        print("    Recommendation: Turn off RAM Expansion / RAM Plus in Settings or via scripts/optimize.py.")

    # 3. Rogue CPU Burners
    print("\n[*] Checking for infamous background CPU hogs & loops...")
    burners = check_known_cpu_burners(target_serial)
    if burners:
        for b in burners:
            print(f"    🚨 DETECTED: {b['name']} ({b['pkg']}) is running (PID: {b['pids']})")
            print(f"       Note: {b['note']}")
    else:
        print("    ✅ No notorious CPU-looping daemons detected.")

    # 4. Animation scales
    scales = check_animation_scales(target_serial)
    print("\n[*] Checking UI compositor animation scales:")
    print(f"  • Window Animation Scale     : {scales['window_animation_scale']}")
    print(f"  • Transition Animation Scale : {scales['transition_animation_scale']}")
    print(f"  • Animator Duration Scale    : {scales['animator_duration_scale']}")
    if scales['window_animation_scale'] in ["1.0", "1"]:
        print("    💡 Tip: Tuning scales to 0.5x via 'scripts/tweak_ui.py' cuts gesture latency by 50%.")

    print("\n" + "="*65)
    print(" ✅ DIAGNOSTIC SUMMARY COMPLETE")
    print(" Run 'python scripts/security_audit.py' for malware & sketchy app checks.")
    print(" Run 'python scripts/optimize.py' to debloat telemetry & fix bottlenecks.")
    print("="*65 + "\n")

if __name__ == "__main__":
    main()
