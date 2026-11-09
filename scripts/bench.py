#!/usr/bin/env python3
"""
scripts/bench.py - Objective Android Frame Pacing & Jank Benchmark Harness

Measures real-world UI smoothness using 'dumpsys gfxinfo <pkg> framestats'.
Calculates exact frame durations, Jank Percentage (>19.1ms for 60Hz), P90/P99 latency,
and 1% Low FPS. Eliminates subjective marketing claims by providing empirical proof of speedup.
"""

import sys
import time
import json
import argparse
from typing import Dict, Any, List, Optional

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from connect import run_adb, get_connected_devices, get_device_info

def calculate_jank_metrics(raw_framestats: str, min_frames: int = 1) -> Dict[str, Any]:
    """
    Parse CSV rows from dumpsys gfxinfo framestats and calculate latency percentiles.
    """
    frame_times_ms: List[float] = []
    lines = (raw_framestats or "").splitlines()
    in_framestats = False

    for line in lines:
        line_str = line.strip()
        if line_str.startswith("---PROFILEDATA---"):
            in_framestats = True
            continue
        if not in_framestats:
            continue
        if line_str.startswith("Flags"):
            continue

        parts = line_str.split(",")
        if len(parts) >= 13:
            flags = parts[0].strip()
            # Flags == 0 indicates standard completed frame without window resize or skip
            if flags != "0":
                continue
            try:
                intended_vsync = int(parts[1])
                # FrameCompleted is column 13; older Android has 14 columns, Android 12+ has 16 columns
                frame_completed = int(parts[13]) if len(parts) >= 14 else int(parts[-1])
                if frame_completed > intended_vsync and intended_vsync > 0:
                    delta_ms = (frame_completed - intended_vsync) / 1_000_000.0
                    if 0.5 < delta_ms < 500.0:  # Filter out system pause artifacts
                        frame_times_ms.append(delta_ms)
            except (ValueError, IndexError):
                continue

    n = len(frame_times_ms)
    if n < min_frames:
        return {
            "error": "Insufficient frames collected. Please scroll or interact with the app during the benchmark.",
            "total_frames": n
        }

    frame_times_ms.sort()
    
    # Jank threshold: 19.1ms (standard for 60Hz display + 15% allowance, or >11.5ms for 90Hz)
    jank_frames = sum(1 for t in frame_times_ms if t > 19.1)
    jank_pct = round((jank_frames / n) * 100.0, 2)
    p50_ms = round(frame_times_ms[int(n * 0.50)], 2)
    p90_ms = round(frame_times_ms[int(n * 0.90)], 2)
    p99_ms = round(frame_times_ms[int(n * 0.99)], 2)
    fps_1pct_low = round(1000.0 / p99_ms, 1) if p99_ms > 0 else 0.0

    return {
        "total_frames": n,
        "jank_frames": jank_frames,
        "jank_percentage": jank_pct,
        "p50_latency_ms": p50_ms,
        "p90_latency_ms": p90_ms,
        "p99_latency_ms": p99_ms,
        "fps_1pct_low": fps_1pct_low
    }

def run_jank_benchmark(
    target_serial: Optional[str] = None,
    pkg: str = "com.android.settings",
    duration: int = 8,
    simulate_scroll: bool = False
) -> Dict[str, Any]:
    """
    Reset gfxinfo, collect framestats over a test window, and parse frame intervals.
    """
    prefix = ["-s", target_serial] if target_serial else []

    # 1. Ensure app is running in foreground
    run_adb(prefix + ["shell", f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1"], timeout=5)
    time.sleep(1.5)

    # 2. Reset graphics buffers
    run_adb(prefix + ["shell", f"dumpsys gfxinfo {pkg} reset"], timeout=5)

    # 3. Workload window (optionally drive automated scrolling for repeatable benchmarks)
    start_time = time.time()
    if simulate_scroll:
        # Perform 3 consistent vertical swipes
        for _ in range(3):
            run_adb(prefix + ["shell", "input swipe 500 1400 500 400 350"])
            time.sleep(1.0)
            run_adb(prefix + ["shell", "input swipe 500 400 500 1400 350"])
            time.sleep(1.0)
    else:
        # Allow user to scroll or wait for interaction
        remaining = duration - (time.time() - start_time)
        if remaining > 0:
            time.sleep(remaining)

    # 4. Dump frame stats
    ok, out = run_adb(prefix + ["shell", f"dumpsys gfxinfo {pkg} framestats"], timeout=10)
    if not ok or not out:
        return {"error": "Failed to retrieve gfxinfo framestats. Ensure app was running."}

    # 5. Calculate metrics
    res = calculate_jank_metrics(out, min_frames=10)
    if "error" in res and res.get("total_frames", 0) < 10:
        return res

    res["app"] = pkg
    res["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return res

def print_benchmark_table(res: Dict[str, Any]):
    print("\n" + "="*60)
    print(" 🏁 UI PERFORMANCE & FRAME PACING BENCHMARK RESULTS")
    print("="*60)
    print(f"  • Tested App Package : {res['app']}")
    print(f"  • Sampled Frames     : {res['total_frames']}")
    print(f"  • Jank Ratio (>19ms) : {res['jank_percentage']}% ({res['jank_frames']} dropped frames)")
    print(f"  • Median Frame Time  : {res['p50_latency_ms']} ms")
    print(f"  • P90 Latency        : {res['p90_latency_ms']} ms")
    print(f"  • P99 Latency        : {res['p99_latency_ms']} ms")
    print(f"  • 1% Low Framerate   : {res['fps_1pct_low']} FPS")
    print("="*60)
    
    if res['jank_percentage'] < 5.0:
        print("  🟢 SMOOTH: Excellent UI pacing with minimal frame drops.")
    elif res['jank_percentage'] < 15.0:
        print("  🟡 MODERATE: Occasional stuttering during heavy animations.")
    else:
        print("  🔴 JANKY: Severe frame drops detected. Optimization strongly recommended.")
    print("="*60 + "\n")

def compare_benchmarks(before_file: str, after_file: str):
    """Compare two JSON benchmark snapshots."""
    with open(before_file, "r", encoding="utf-8") as f:
        b = json.load(f)
    with open(after_file, "r", encoding="utf-8") as f:
        a = json.load(f)

    print("\n" + "="*70)
    print(" 📊 BEFORE vs AFTER OPTIMIZATION PERFORMANCE COMPARISON")
    print("="*70)
    print(f"{'Metric':<25} | {'Before':<15} | {'After':<15} | {'Improvement'}")
    print("-" * 70)
    
    jank_diff = b['jank_percentage'] - a['jank_percentage']
    jank_arrow = "🟢" if jank_diff >= 0 else "🔴"
    print(f"{'Jank Percentage':<25} | {b['jank_percentage']}%{'':<10} | {a['jank_percentage']}%{'':<10} | {jank_arrow} {abs(jank_diff):.1f}% reduction")

    p90_diff = b['p90_latency_ms'] - a['p90_latency_ms']
    p90_arrow = "🟢" if p90_diff >= 0 else "🔴"
    print(f"{'P90 Latency':<25} | {b['p90_latency_ms']} ms{'':<8} | {a['p90_latency_ms']} ms{'':<8} | {p90_arrow} {abs(p90_diff):.1f} ms faster")

    p99_diff = b['p99_latency_ms'] - a['p99_latency_ms']
    p99_arrow = "🟢" if p99_diff >= 0 else "🔴"
    print(f"{'P99 Latency':<25} | {b['p99_latency_ms']} ms{'':<8} | {a['p99_latency_ms']} ms{'':<8} | {p99_arrow} {abs(p99_diff):.1f} ms faster")

    fps_diff = a['fps_1pct_low'] - b['fps_1pct_low']
    fps_arrow = "🟢" if fps_diff >= 0 else "🔴"
    print(f"{'1% Low FPS':<25} | {b['fps_1pct_low']} FPS{'':<7} | {a['fps_1pct_low']} FPS{'':<7} | {fps_arrow} +{fps_diff:.1f} FPS boost")
    print("="*70 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Android Frame Pacing & Jank Benchmark Harness")
    parser.add_argument("--app", default="com.android.settings", help="Target app package to benchmark (default: com.android.settings)")
    parser.add_argument("--duration", type=int, default=8, help="Measurement window in seconds (default: 8)")
    parser.add_argument("--scroll", action="store_true", help="Simulate automated swipe gestures for repeatable results")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--save", type=str, help="Save benchmark results to JSON file")
    parser.add_argument("--compare", nargs=2, metavar=("BEFORE_JSON", "AFTER_JSON"), help="Compare two benchmark snapshots")
    args = parser.parse_args()

    if args.compare:
        compare_benchmarks(args.compare[0], args.compare[1])
        return

    devices = get_connected_devices()
    auth = [d for d in devices if d["status"] == "device"]
    if not auth:
        print("❌ No authorized Android device connected. Run 'python scripts/connect.py' first.")
        sys.exit(1)

    target_serial = auth[0]["serial"]
    info = get_device_info(target_serial)
    
    if not args.json:
        print(f"\n[*] Launching benchmark on: {info['brand'].upper()} {info['model']} ({args.app})...")
        if args.scroll:
            print("    Simulating automated touch scrolls...")
        else:
            print(f"    Please interact with / scroll inside {args.app} for {args.duration}s...")

    res = run_jank_benchmark(
        target_serial=target_serial,
        pkg=args.app,
        duration=args.duration,
        simulate_scroll=args.scroll
    )

    if "error" in res:
        print(f"❌ Error: {res['error']}")
        sys.exit(1)

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        if not args.json:
            print(f"📁 Benchmark snapshot saved to: {args.save}")

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print_benchmark_table(res)

if __name__ == "__main__":
    main()
