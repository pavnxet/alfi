# Contributing to Android Lag Fixer

We welcome contributions to make Android devices cleaner, faster, and more responsive!

## How You Can Contribute
1. **Device Reports & Fix Fixtures**: If you have tested a device, share `getprop ro.product.model`, `ro.build.version.sdk`, and OEM skin details.
2. **Package Database Additions**: Submit new bloatware, telemetry, or adware definitions to `package_database.json` with appropriate risk tiers (`Recommended`, `Advanced`, `Expert`, `Unsafe`).
3. **Benchmarking**: Share before-and-after `scripts/bench.py` benchmark deltas across different OEM builds.

## Pull Request Guidelines
- All code must pass unit tests: `pytest tests/`
- Respect the zero-brick guarantee: NEVER mark critical system subsystems (WebView, Telephony, OTA updaters, Account managers) as `Recommended` or `Advanced`.
