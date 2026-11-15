# Android Health & Performance Doctor 🩺📱

🌐 **Language / Limba:** **[🇬🇧 English](README.md)** | **[🇷🇴 Română](README.ro.md)**

### Universal ADB Diagnostic & Optimization Suite (USB & Wireless Wi-Fi) for Any Android Device

**Android Health Doctor** is a rootless Web + CLI diagnostic and repair suite designed to identify and fix the real root causes behind Android UI stutter (*jank / frame drops*), RAM/ZRAM exhaustion, corrupted system databases, and **"Application Not Responding" (ANR)** freezes across all Android brands (**Samsung Galaxy, Google Pixel, Xiaomi, OnePlus, Motorola, Asus, Nothing, Sony**, etc.).

---

## 🟢 Option 1: Standalone Windows Application (No Python or ADB Required!)

For users who **do not have Python or Android Platform Tools installed**:
1. **[📥 Click here to download `AndroidHealthDoctor.exe` (Portable 1-File App)](dist/AndroidHealthDoctor.exe)** (or download from the **[Releases](../../releases)** page).
2. Double-click **`AndroidHealthDoctor.exe`**.
   - Everything is pre-packaged inside the executable: Python runtime, Web UI, and official Google `adb.exe` drivers!
   - Even if `adb.exe` is ever missing on a system, the app automatically downloads the official Google Android Platform Tools (~6 MB) in the background.
3. Your browser will open automatically at `http://127.0.0.1:8899`.

---

## ✨ Key Features & Deep Diagnostics

1. **System Content Providers & SQLite Database Repair (`android.process.acore`, `MediaStore`, `Downloads`, `GSF`)**:
   - When the Android Contacts database (`com.android.providers.contacts` / `acore`) or MediaStore index (`com.android.providers.media.module`) becomes corrupted or stuck in a sync loop, every app that queries contacts, keyboard autofill, or storage (WhatsApp, Phone, Messages, Gallery, Chrome) freezes for seconds at a time.
   - Rebuilds corrupted local SQLite provider databases cleanly and AOT-compiles them in native `speed` mode (cloud contacts re-sync automatically within seconds).

2. **GPU Frame Drop (UI Jank) Analysis & Accessibility Hook Detection**:
   - Parses `dumpsys gfxinfo` to measure **Janky Frames (%)** and 95th/99th percentile frame render times per application.
   - Detects active **Accessibility Services** (auto-clickers, overlay utilities, macro tools) that intercept touch input and cause severe scrolling micro-stutter and `Input dispatching timed out` ANRs.
   - Automatically detects the **device's default home launcher** (One UI Home, Pixel Launcher, MIUI/HyperOS Home, Nova, etc.), clears corrupted shader caches, and forces native `speed` compilation on the Launcher, `SystemUI`, and `Android System WebView`.

3. **Deep Per-App Repair (Without Wiping User Accounts)**:
   - Includes a searchable **Installed App Explorer** for all apps on the device.
   - **Safe Repair (`🔧 Repair & Speed Compile`)**: Force-stops hung threads (`am force-stop`), clears *only* corrupted cache (`pm clear --cache-only`, preserving login sessions and user data!), and compiles the package Ahead-of-Time (`cmd package compile -m speed -f`).
   - **Background Restriction (`🛑 Restrict Background`)**: Places parasitic background apps into `Standby Bucket: restricted` and blocks `RUN_ANY_IN_BACKGROUND`.

4. **RAM, ZRAM Swap & Kernel PSI (Pressure Stall Information)**:
   - Monitors RAM and ZRAM saturation alongside Linux kernel `/proc/pressure/{cpu,memory,io}` stall metrics.
   - Stops parasitic background daemons (unused local AI services, telemetry, excessive debug ring buffers) and enables the Android *Cached App Freezer*.

5. **Dual Connection Mode: USB Cable & Wireless ADB (100% Cable-Free)**:
   - Perfect for devices with worn or broken USB ports: includes automatic **mDNS discovery** (`adb mdns services`), 6-digit pairing code support (`adb pair`), and direct Wi-Fi connection (`adb connect`).
   - Built-in **Real-Time Execution Console** with live step-by-step progress bar, timer, and live background compiler (`dex2oat64` / `fstrim`) monitoring.
   - Built-in **🇬🇧 EN / 🇷🇴 RO** instant language switcher in the Web UI.

---

## 🛠️ Option 2: Run from Python Source (For Developers)

### 1. Prerequisites
- **Python 3.9+** (ADB is automatically downloaded if not already installed!)
- Install Python dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### 2. Launch Web UI
Double-click `run.bat` (on Windows) or run:
```bash
python main.py
```

### 3. Build Standalone `.exe` Yourself
Double-click `build_exe.bat` or run:
```bash
python build_exe.py
```
This produces `dist/AndroidHealthDoctor.exe` with Python + Web UI + `adb.exe` bundled inside a single portable file.

### 4. Launch CLI Mode
```bash
# Run full diagnostic scan (English default, add --ro for Romanian)
python cli.py

# Run scan + automatically apply all deep repairs
python cli.py --fix
```

---

## 📱 How to Enable USB or Wireless Debugging on Android
1. Open **Settings** &rarr; **About phone**.
2. Tap **Build number** (or MIUI/OS Version) **7 times** rapidly until you see *"You are now a developer!"*.
3. Open **Settings** &rarr; **System / Additional settings** &rarr; **Developer options**:
   - **For USB Cable**: Enable **USB debugging**, connect the cable, and tap **Allow** on the phone prompt.
   - **For Wi-Fi (No Cable)**: Enable **Wireless debugging**, tap on the **Wireless debugging** text to open its menu, and use the **📶 Wireless ADB** panel in the web app.
