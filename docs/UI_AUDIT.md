# UI audit — Phase 0

**Commit audited:** `ac25c5b` (branch `main`, repo now `pavnxet/alfi`)
**Baseline:** `python -m pytest tests/ -q` → **107 passed**. `python -m unittest discover tests` → same (CI uses this runner).
**Purpose:** confirm or correct the `[verify]` items in the TUI enhancement brief before changing anything.

---

## 1. Corrections to the brief

| Brief said | Reality |
| --- | --- |
| "README claims 107 passing tests" | Correct at the time of writing. The suite is now 143 with the new UI tests. |
| "roughly 74 columns wide" | Yes — but the *rendered* width was 92. See §3.1. |
| "likely plain `input()`" | Correct, and it is load-bearing: `tests/test_wizard.py` patches `builtins.input` with fixed `side_effect` lists, so the number and order of `input()` calls per screen is an implicit contract. Any prompt refactor must preserve it. |
| "raw ANSI" | Correct — colour literals were re-declared inside individual functions (`modes.confirm_preflight_plan`, `modes.print_preflight_report`, `wizard.print_device_card`), each with its own local copy. |
| "No third-party dependencies" | Correct and enforced: `pyproject.toml` has `dependencies = []`. |

## 2. What already existed (and why it did not help)

`scripts/wizard.py` already had `strip_ansi()`, `vlen()` and `pad_box_line()`. They were **not** used consistently, and `vlen()` has a specific defect:

```python
w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
```

Emoji are category `N` (neutral) in `east_asian_width`, so `🚀` counted as **1** column while terminals draw it in **2**. Every row containing an emoji was therefore padded one cell short per emoji.

## 3. Confirmed defects (all reproduced, all now fixed)

### 3.1 Menu rows overflowed their own box — 92 columns inside a 74-wide frame

```python
width = 74
print(f"{C_BORDER}│{C_RESET}{content:<90}{C_BORDER}│{C_RESET}")   # 92 visible columns
```

Measured on the rendered dashboard: `distinct widths: [38, 44, 48, 49, 61, 62, 63, 65, 66, 67, 68, 69, 70, 71, 72, 74]`. The right border of every menu row sat 18 columns past the box top.

Same class of bug in `modes.print_preflight_report` (`{title:<90}` inside a 74-wide frame) and in `wizard.prompt_device_selection`.

### 3.2 Two more copies of the same layout code

`prompt_mode_selection` built its four mode cards by hand with `print()` calls; `print_preflight_report` built its own card; `print_device_card` built a third. Three implementations, three different padding rules, no shared width.

### 3.3 Non-TTY behaviour was partially fixed but not centralised

`clear_screen()` respected `NO_COLOR` and the `isatty` check, but colour constants were unconditional, so piped output still carried escape sequences. There was no single write path to fix this in one place.

## 4. What the refactor changed

- `scripts/ui/` — `term` (capability detection), `theme` (one semantic palette), `widgets` (pure renderers), `keys` (raw keypress), `prompts` (validated input).
- `widgets.display_width()` counts ANSI as 0 and emoji/CJK as 2; every pad and truncate goes through it.
- `wizard.py` and `modes.py` now render through `ui.box()` / `ui.kv()` / `ui.badge()` / `ui.progress()`.
- One write path (`ui.out()`), so non-TTY, `NO_COLOR` and `ALFI_ASCII` are handled once.

## 5. Deliberately not changed

- `input()` call counts and order on every existing screen (tests depend on them).
- The manifest-before-mutation ordering, the allowlist, the dependency graph, Ultra's `I UNDERSTAND` gate, `--yes`, `--dry-run`, `--json` semantics.
- `operations.py`, `restore.py`, `rescue.py` logic.
- `package_database.json` content.

## 6. Known gaps after this pass

- Arrow-key navigation exists in `ui.keys` / `ui.prompts.select` but is only wired for future use; the dashboard still takes typed keys, which is what every script and test relies on today.
- The package detail view pages at 12 packages per card rather than being scrollable.
- `--status`, `--theme` and `--no-emoji` flags are not implemented (the env vars `NO_COLOR` and `ALFI_ASCII` cover the common cases).
