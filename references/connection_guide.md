# Android Device Connection & Troubleshooting Manual

This guide walks you through connecting your Android smartphone to a PC via **USB Cable** or **Wireless Debugging (Wi-Fi)**.

---

## 1. Enabling Developer Options

Android hides developer tools by default to prevent accidental configuration changes.

1. Open **Settings** on your phone.
2. Scroll to the bottom and select **About Phone** (or **About Device**).
3. Find **Build Number** (on Realme/Oppo/Xiaomi: go into **Software Information** or **Version**).
4. Tap **Build Number** continuously **7 times**.
5. You will see a toast notification: *"You are now a developer!"*.

---

## 2. Enabling USB Debugging

1. Go back to main **Settings**.
2. Look for **Developer Options**:
   - On Samsung: At the very bottom of the main Settings screen.
   - On Realme / Oppo / OnePlus: Under **Additional Settings** > **Developer Options**.
   - On Xiaomi / Poco: Under **Additional Settings** > **Developer Options**.
   - On Stock Android / Pixel / Motorola: Under **System** > **Developer Options**.
3. Toggle **USB Debugging** to **ON**.
4. *(Crucial for Xiaomi & Realme)*:
   - Also enable **Install via USB**.
   - Enable **USB Debugging (Security settings)** if available.

---

## 3. Physical Cable Connection & Host Authorization

1. Connect the phone to your PC using a **USB data cable** (ensure the cable supports high-speed data transfer, not power-only charging).
2. Unlock your phone's screen.
3. A popup dialog will appear: **"Allow USB debugging?"** with the computer's RSA key fingerprint.
4. **IMPORTANT**: Check the box: ☑ **"Always allow from this computer"**.
5. Tap **Allow** or **OK**.
6. Verify on your PC terminal:
   ```bash
   adb devices
   ```
   It should output: `<device_serial> device`.

---

## 4. Wireless Debugging Setup (Android 11+)

If you do not have a USB data cable or prefer cable-free management:

1. Ensure your PC and Phone are connected to the **same Wi-Fi network**.
2. On your phone: Go to **Settings** > **Developer Options** > **Wireless Debugging**.
3. Toggle it **ON**.
4. Tap **Pair device with pairing code**.
5. You will see:
   - Wi-Fi pairing code (e.g. `123456`)
   - IP address & Port (e.g. `192.168.1.50:37891`)
6. On your PC terminal, run:
   ```bash
   python scripts/connect.py --pair 192.168.1.50:37891 123456
   ```
7. Once paired, note the main Wireless Debugging IP & Port shown on the phone screen (e.g. `192.168.1.50:41235`), then connect:
   ```bash
   python scripts/connect.py --connect 192.168.1.50:41235
   ```

---

## 5. Troubleshooting Connection Issues

| Symptom | Cause | Solution |
|---|---|---|
| Device shows `unauthorized` in `adb devices` | Screen was locked or RSA prompt was dismissed | Wake phone, unplug and re-plug cable, tap "Revoke USB debugging authorizations" in Developer Options, then plug in again. |
| Device does not show at all | Missing USB Drivers or charge-only cable | 1. Test a different USB port/cable.<br/>2. Install OEM drivers: Samsung Smart Switch, Google USB Driver via Android Studio, or universal ADB driver. |
| Device shows `offline` | ADB daemon communication glitch | Run `adb kill-server` followed by `adb start-server`. |
