# ALFi — deep audit & capability plan (v2)

**Repo:** `pavnxet/alfi` · **Branch audited:** `feat/unified-cli` @ `9a881e9` (+2 local commits) · **Date:** 2026-11-10
**Method:** full test run, coverage measurement, lint pass, static reading of all 21 modules, web research on Android internals, competitor feature audit, and Reddit/XDA threads where users describe what actually fixed their phones.
**This document is a plan, not a patch.** Nothing below is implemented yet.

---

## 0. Summary

| | Now | After this plan |
| --- | --- | --- |
| Diagnostics | CPU load, RAM %, swap %, battery, jank % | **stall-time attribution, thermal budget, dexopt state, wakeup attribution, leak trend** |
| Evidence quality | heuristic ("RAM is 84%, maybe zram") | measured ("memory stalls 3.1 s/min, 68% from app X") |
| Actions | disable packages, appops, animations, ART | + **suspend**, targeted dexopt, post-reboot verification, leak remediation |
| Test coverage | 50% (optimize.py at 0%) | ≥ 70%, no module under 40% |
| Commands | 19 | 24 (`probe`, `attrib`, `verify`, `leak`, `jank`) |

The strategic gap is simple: **ALFi currently measures resources, not the thing users feel.** "84% RAM used" is not a symptom; "the kernel spent 3 seconds per minute stalled on memory" is. Android already exposes that number, and no desktop ADB tool in this space reads it.

---

## 1. Evidence base

### 1.1 What users actually report

Read from r/Xiaomi, r/Android, r/AndroidQuestions, r/LineageOS, r/oneplus and XDA threads:

- **Lag returns after an OTA, and a reboot clears it for a while.** Pixel 9a thread: *"whenever it slows down, if I restart the device, it is back to normal… eventually after many weeks it slows down again."* → symptom of a leaking service, not of too many packages. Our tool has no way to see growth over time today.
- **A single system service can be the whole problem.** Same thread: *"go to running services and see if Settings is using an absurd amount of ram. Settings Dump Service is usually bugged now and uses crazy amount of resources."* → the fix is one process, not a debloat list.
- **User-level fixes that recur**: limit widgets, toggle RAM Plus / memory extension off, cap refresh rate at 60 Hz, remove SD card, reboot daily. *"Don't expect miracles"* — the community is realistic; our tool should be too.
- **Battery drain after an OTA is the other half of the same complaint** (r/oneplus "Battery Drain SOLVED", "Significant battery drain after Oxygen OS 15 update").
- **Xiaomi/HyperOS specific**: unlink the Mi account before removing system apps to avoid bootloops (XDA HyperOS guide); removing Powerkeeper made performance *worse* on Geekbench/3DMark — a reminder that "aggressive" is not "better".
- **Debloaters report success while OEMs silently restore packages after reboot** — documented for Canta: *"Some OEMs (specific Samsung and Xiaomi builds) restrict package removal even over ADB, so Canta reports success but the app returns after a reboot."* Nobody verifies across a reboot. That is an open, valuable feature.

### 1.2 What the competitors ship

| Tool | Capabilities worth matching | What we can beat them on |
| --- | --- | --- |
| **UAD-ng** | 5,399-package list, 4 risk tiers, dependency graph, CLI with `--dry-run` | measurement, attribution, verification |
| **Canta** | on-device via Shizuku, restore list | post-reboot verification (they lack it) |
| **Hail** | three freeze modes: **disable / hide / suspend** | suspend is one command we don't use |
| **SD Maid SE** | CorpseFinder (leftover files), AppCleaner, StorageAnalyzer | not our scope, but "storage pressure" belongs in diagnosis |
| **App Manager** | net policy, app ops, battery optimisation control, tracker scan | we have appops + doze already |

The feature gap we should close: **suspend** (Hail), **post-reboot verification** (nobody), and **net policy** (App Manager).

### 1.3 What Android exposes that ALFi does not use

| Signal | Command | Why it matters |
| --- | --- | --- |
| **PSI stall time** | `cat /proc/pressure/{memory,io,cpu}` | Google's own metric for "how long tasks waited"; lmkd uses it to decide kills. Lag *is* stall time. |
| **Thermal status** | `dumpsys thermalservice` | status 0–6 plus per-zone °C; explains "fast then slow" |
| **Dexopt state** | `dumpsys package dexopt` | shows `actualCompilerFilter` per app — tells you which apps are still interpreted |
| **Background dexopt** | `cmd package bg-dexopt-job` | runs profile-guided compilation for all apps, ~40 s |
| **Cold start** | `am start -W -n pkg/activity` | `TotalTime`/`WaitTime` per app, the number users feel |
| **Wakeups** | `dumpsys alarm`, `dumpsys power` | per-package alarm counts and wakelocks |
| **Suspend** | `pm suspend <pkg>` | reversible freeze that keeps the icon greyed out |
| **Boot identity** | `cat /proc/sys/kernel/random/boot_id` | lets us prove a package stayed disabled across a reboot |

Three of these (PSI, thermalservice, dexopt) are documented public interfaces — this is not rooting around in private internals.

---

## 2. Repo debug findings (current branch)

Measured today: **180 tests pass**, **50% coverage**, **6,439 LOC** in `scripts/` + 1,017 in `scripts/ui/`, 17 broad `except Exception`, 36 duplicated `prefix = ["-s", serial]` builders, 3 copies of the ASCII banner, 0 TODO markers.

| ID | Severity | Finding | Evidence |
| --- | --- | --- | --- |
| D1 | **P1** | `optimize.py` has **0% coverage** and no test file — the oldest, most-used debloater path is entirely untested | `--cov` report |
| D2 | P1 | 36 hand-built `["-s", serial]` prefixes; no `Device` object, so timeouts/retries/JSON can't be applied consistently | `grep -c` |
| D3 | P1 | 17 blind `except Exception` (6 in `modes.py`, 5 in `wizard.py`) — a failure in the manifest path is swallowed silently | `grep -c` |
| D4 | P2 | Three copies of the banner/box layout (wizard, modes, monitor) — theme changes must be made 3× | `grep "█████"` |
| D5 | P2 | No post-reboot verification: a package OEMs restore on boot is reported as "disabled" forever | feature gap |
| D6 | P2 | `diagnose.py` infers memory trouble from load average and RAM %, not from stalls | code read |
| D7 | P2 | Jank is one number (%), with no attribution to pipeline stage | `bench.py` |
| D8 | P3 | Benchmarks are single-shot; no repeat/median protocol, so run-to-run noise can exceed the effect | `bench.py` |

None of these are correctness emergencies — the v1.2.0 QA round fixed the silent-failure class. They are the ceiling on how much the tool can *prove*.

---

## 3. New methods (the inventive part)

Each method is a measurable signal + a threshold + an interpretation, so the tool can say *what* is wrong instead of *that* something is wrong.

### M1 — Stall-time lag attribution (PSI)

**Read:** `cat /proc/pressure/memory /proc/pressure/io /proc/pressure/cpu`
**Format:** `some avg10=… avg60=… avg300=… total=…` (+ `full` for memory/io)
**Metric:** *stall seconds per minute* = `Δtotal_us / 60e6`, plus `full` share.
**Interpretation ladder**

| memory `some` avg60 | verdict |
| --- | --- |
| < 1% | memory is not your problem — stop blaming RAM |
| 1–5% | mild pressure; zram sizing worth a look |
| 5–20% | real stutter source; find the allocator (M4/M5) |
| > 20% or `full` > 5% | thrashing; lmkd will start killing apps |

**Why it's better:** it is the same signal Android's own `lmkd` uses, it needs one shell line, and it separates "RAM is full because Android caches everything" (normal) from "tasks are actually waiting" (bad). This single metric replaces most of `diagnose.py`'s guesswork.
**Fallback:** kernels without PSI → `/proc/vmstat` (`pswpin`, `pswpout`, `pgscan_direct`, `pgmajfault`) deltas.

### M2 — Thermal budget

**Read:** `dumpsys thermalservice`
**Gotchas to encode:** check `IsStatusOverride` **first** (a stale override makes every reading a lie); status is 0–6; thermalservice prints °C as float, `dumpsys battery` prints tenths, `/sys/class/thermal/*/temp` prints thousandths — three scales, three conversions.
**Metric:** *throttle minutes per session*, plus `headroom` = minutes of sustained load before status reaches 2.
**Why:** explains "fast for ten minutes, then laggy" — a thermal story no debloat fixes, and one that users misattribute to bloatware.

### M3 — Dexopt state audit

**Read:** `dumpsys package dexopt` → per-package `status=` / `actualCompilerFilter=`
**Metric:** % of *user-visible* apps compiled at `speed-profile` or `speed`.
**Action:** compile only the apps left at `verify`: `cmd package compile -m speed-profile -f <pkg>`, then `cmd package bg-dexopt-job` for the rest.
**Why:** "speed-profile" is the difference between interpreted-on-first-run and AOT; it is a real, measurable startup win and currently ALFi compiles a blind list of five packages instead of the ones that need it.

### M4 — Wakeup attribution

**Read:** `dumpsys alarm` (per-package alarm counts), `dumpsys power` (wakelocks), `dumpsys deviceidle`
**Metric:** wakeups/hour per package, wakelock ms/hour.
**Output:** top-10 table with "share of total wakeups", joined against the package DB tier so the user sees *who* and *how risky*.

### M5 — Runaway process detector

**Read:** `ps -A -o PID,RSS,NAME` (fallback `dumpsys meminfo`)
**Rule:** flag any process with RSS > 400 MB, or > 25% of total RAM, **and** a package name in the system namespace — this is the "Settings Dump Service eating 2 GB" case from the Pixel thread.
**Output:** ranked list + the exact `am force-stop` / disable suggestion, with a warning when the process is a critical service.

### M6 — Leak watch (trend across runs)

**Idea:** the vault already stores per-device history. Store one line per run: timestamp, per-process RSS, PSI totals, battery %.
**Metric:** linear slope of RSS per process over ≥3 runs → *"com.example +18 MB/day, 4 samples over 6 days"*.
**Why:** this is the only way to answer "why does my phone get slow after two weeks and a reboot fixes it". No competitor does it.

### M7 — Post-reboot verification

**Read:** `/proc/sys/kernel/random/boot_id` before and after.
**Flow:** `alfi apply` → record boot_id + disabled set → `alfi verify --after-reboot` → diff → *"3 packages came back (OEM restored them)"*.
**Why:** directly fixes the known Canta/UAD failure mode where success is reported but the OEM silently undoes it.

### M8 — Jank fingerprint

**Read:** `dumpsys gfxinfo <pkg> framestats` (already parsed) — but use the *stage* columns, not just total.
**Metric:** per-stage medians: input→animation, animation→traversal, traversal→draw, draw→sync, sync→gpu; classify each janky frame by its dominant stage.
**Output:** *"72% of your janky frames are draw-bound (issue-draw-commands), not GPU-bound"* → tells the user whether to reduce blur/shadows (app side) or look at the GPU governor (system side).

### M9 — Cold-start leaderboard

**Read:** `am start -W -n <pkg>/<launcher activity>` → `TotalTime`, `WaitTime`
**Metric:** median of 3 launches, per app, before/after.
**Why:** startup is the number users judge; it is also stable enough to A/B (unlike jank %).

### M10 — Suspend as a softer freeze

**Action:** `pm suspend <pkg>` (Android 7+), reversible with `pm unsuspend`.
**Why:** between "disable" (icon disappears, user panics) and "leave it" — the icon greys out, the app can't run, and it survives less destructively. Hail exposes this; ALFi does not.

---

## 4. Roadmap

Each phase ships independently, keeps the suite green, and has explicit acceptance criteria.

### Phase 1 — Measurement core (the foundation)

| Item | Command | Acceptance |
| --- | --- | --- |
| `alfi probe` | PSI + thermal + battery + memory in **one** adb call | prints a panel; `--json` returns all fields; < 1.5 s on USB |
| `alfi probe --watch` | reuse `monitor.py` | sparkline shows PSI `some avg10` over time |
| `diagnose.py` rework | PSI-first verdicts | old load-average output kept as a secondary panel |
| Thermal panel | status + hottest 3 zones + override warning | refuses to report status when `IsStatusOverride: true` |

**Tests:** fixture-driven parsing for PSI (some/full, all three windows), thermalservice (with and without override, 0.0 values, NaN), `vmstat` fallback. **Safety:** read-only.

### Phase 2 — Attribution

`alfi attrib` = wakeups (M4) + runaway processes (M5) + jank fingerprint (M8) + dexopt state (M3), each behind a flag, all in one command with `--json`.
**Acceptance:** every table sorts by impact, shows a share-of-total column, and joins the package DB for a risk badge. **Tests:** recorded fixtures per OEM (Samsung, Redmi, Pixel already exist; add one HyperOS and one ColorOS).

### Phase 3 — Actions that use the measurements

| Action | Rule |
| --- | --- |
| `alfi dexopt --targets` | compile only apps at `verify`, never the whole device |
| `alfi suspend <pkg>` | new verb; refuses system-critical packages; `--unsuspend` |
| `alfi verify --after-reboot` | M7 flow with a manifest diff |
| `alfi apply` (existing modes) | gains a post-run PSI delta in the session summary |

**Acceptance:** every action is `--dry-run` capable, writes the manifest before mutating (already true), and reports the *measured* delta after.

### Phase 4 — Trend and history

`alfi leak` (M6) + `alfi history` (existing vault, rendered) + `alfi compare <run-a> <run-b>`.
**Acceptance:** ≥3 samples produce a slope with a confidence note ("3 samples — indicative, not proof").

### Phase 5 — Hardening the repo (D1–D4)

1. `optimize.py` tests (it is at 0%).
2. `Device` object replacing 36 prefix builders; timeouts, retries, `--json` in one place.
3. Replace blind excepts with `errors.py` classes; log instead of swallowing.
4. One banner/card renderer used by wizard, modes and monitor.

**Acceptance:** coverage ≥ 70%, no module < 40%, `ruff check` clean on `scripts/`, and a `--json` contract test that runs every command with `--json` and asserts valid JSON.

### Phase 6 — Release

`v1.3.0`: CHANGELOG, README tables for the new commands, SKILL.md updated, CI matrix green on 3.9–3.13 × 3 OS, wheel smoke test (already in CI).

---

## 5. Test strategy

| Layer | What |
| --- | --- |
| Parsers | fixture files per command per OEM (`/proc/pressure/*`, `thermalservice`, `dexopt`, `alarm`, `ps`) — these are the tests that catch the class of bug we hit three times (fixture matches parser, not device) |
| Contract | every `alfi <cmd> --json` must parse; every mutating command must accept `--dry-run` and touch nothing |
| Safety | manifest-before-mutation, allowlist, Ultra gate, and "suspend never touches a critical package" — asserted through the new paths |
| Determinism | no test may call a real `adb` (currently enforced by PATH isolation — keep it) |
| Regression | one test per historical bug: Android 17 uninstall block, HyperOS `Cannot disable`, `pm enable` exit-0 refusal, empty `sdk_level`, PSI-absent kernel |

---

## 6. Risk register

| Risk | Mitigation |
| --- | --- |
| PSI absent (kernels < 4.14 or `CONFIG_PSI` off) | fallback to `/proc/vmstat` counters; state which path was used |
| OEM dumps vary wildly (`mName` not standardised) | read fields by name, never by position; treat unknown as unknown |
| Thermal override left on by another tool | always print `IsStatusOverride`; refuse to interpret when true |
| Extra adb calls slow the dashboard | one combined shell line per panel; cache per screen entry |
| Dexopt can take minutes and heat the device | `--dry-run` first, show target count and estimated time, require `--yes` for >20 apps |
| Suspend is not the same as disable on all OEMs | capability probe; fall back to disable with a clear message |
| Leak slope from 3 points is noise | label as indicative, require ≥5 points for "trend" |

---

## 7. What I deliberately excluded

Root-only features (kernel governors, Magisk modules, partition edits), APK backup/restore (App Manager's job), file-manager and storage cleanup (SD Maid's job), tracker-signature scanning of installed APKs (needs the APK on the PC — violates host isolation), and any cloud/telemetry endpoint.

---

## 8. Sequencing

Phase 1 → 2 → 3 is the value spine (measure → attribute → act) and can ship in three PRs. Phase 5 is cleanup that should land *with* Phase 3, because the new commands double the prefix-builder count otherwise. Phase 6 last.

Rough effort: P1 ~2 days, P2 ~2 days, P3 ~2 days, P4 ~1 day, P5 ~2 days, P6 ~half day.

---

## Appendix A — feasibility check (done, not committed as code)

M1's parser and verdict ladder were prototyped and validated before writing this plan, so Phase 1 is not speculative:

```
parsed some.avg60 = 1.85 | full.avg60 = 0.42  ->  "mild pressure"
  some=0.5   full=0.0  -> memory is not your problem   OK
  some=3     full=0.2  -> mild pressure                OK
  some=12    full=1    -> real stutter source          OK
  some=25    full=2    -> severe                       OK
  some=10    full=7    -> thrashing                    OK
ladder: all pass
```

The first draft of the parser crashed on `total=81234567` (splitting on `=` twice); the fixed version is the one above. That is the class of bug the fixture tests in §5 exist to catch.

## Appendix B — the one-line pitch for each new command

| Command | Pitch |
| --- | --- |
| `alfi probe` | "Is my phone actually stalling, or just caching RAM?" |
| `alfi attrib` | "Which app is causing it?" |
| `alfi leak` | "Why is it slow again two weeks after a reboot?" |
| `alfi verify` | "Did the OEM undo my debloat overnight?" |
| `alfi jank` | "Is my stutter draw-bound or GPU-bound?" |
| `alfi dexopt --targets` | "Which apps are still interpreted?" |
| `alfi suspend` | "Freeze it without making the icon vanish." |
