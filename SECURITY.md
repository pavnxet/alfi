# Security Policy

## Security Guarantees
- **Host PC Isolation**: Android Lag Fixer executes all diagnostics and package modifications remotely in the Android userland via ADB text streams. It never downloads, mounts, or executes Android binaries (`.apk`, `.dex`, `.so`) on your host machine.
- **No Network Uploads**: The tool does not transmit telemetry, device identifiers, or usage data to any remote server.
- **Non-Root**: Operates strictly within standard unprivileged ADB permissions.

## Reporting Security Issues
If you discover a security vulnerability or accidental command injection vector, please open a private security advisory on GitHub or email the maintainer.
