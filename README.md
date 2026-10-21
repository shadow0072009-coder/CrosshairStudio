# 🎯 Crosshair Studio Pro

A customizable **crosshair overlay** for Windows games (CS2, Valorant, CS 1.6, and more).
Design your perfect crosshair, analyze crosshairs from screenshots, and overlay it
directly on your screen — no game config needed.

## ✨ Features

- **Crosshair Designer** — choose style (Cross, Dot, Cross+Dot, Circle, T-shape), length,
  thickness, gap, dot size, color, outline, and fine X/Y offset with a **live preview**
- **Image Analysis (AI)** — upload any crosshair screenshot and the app detects its
  color, style, size, thickness, and gap automatically
- **Profiles & Sharing** — save/load profiles as `.json`, or share a crosshair with a
  single **Share Code** (CRX-...)
- **Built-in presets** — AWP Dot, CS 1.6 Classic, Valorant Cyan, and more
- **Click-through overlay** — sits at screen center, always on top, and never blocks
  your game or mouse
- **Hotkey** — press `F8` to toggle the crosshair on/off instantly
- **Multi-language UI** — English, O'zbek, Русский (choice is remembered)

## 🚀 Quick Start (from source)

Requirements: Python 3.10+ on Windows.

```bash
pip install -r requirements.txt
python main.py
```

Or just double-click `Start-CrosshairStudio.bat`.

## 📦 Build the .exe

Double-click `build_exe.bat`, or run manually:

```bash
pip install pyinstaller
python make_icon.py
python -m PyInstaller --noconfirm --onefile --windowed --name CrosshairStudioPro --icon icon.ico --collect-all customtkinter --hidden-import win32api --hidden-import win32gui --hidden-import win32con --hidden-import pywintypes main.py
```

The finished app appears at `dist/CrosshairStudioPro.exe` (~32 MB). It is
self-contained — no Python install needed on the target machine.

## 🧪 Tests

```bash
python test_crosshair.py   # full suite: config, renderer, analyzer, overlay, i18n, lifecycle
python test_exe.py         # launches the built exe and verifies it runs
```

## 🎮 Usage

1. Launch the app — the crosshair appears at the center of your screen
2. Tune it in the **Designer** tab (live preview updates instantly)
3. Press `F8` to show/hide, or use the toggle in the title bar
4. Found a crosshair you like in a screenshot? Use the **Image Analysis** tab

> The overlay is click-through and always on top, so it works while you play.

## 📄 License

MIT — free to use, modify, and share.
