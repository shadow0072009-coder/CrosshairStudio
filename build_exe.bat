@echo off
title Building Crosshair Studio Pro...
cd /d "%~dp0"

echo [1/3] Installing build dependencies...
python -m pip install --quiet pyinstaller

echo [2/3] Generating icon...
python make_icon.py

echo [3/3] Building exe (this can take a minute)...
python -m PyInstaller --noconfirm --onefile --windowed ^
    --name CrosshairStudioPro ^
    --icon icon.ico ^
    --collect-all customtkinter ^
    --hidden-import win32api ^
    --hidden-import win32gui ^
    --hidden-import win32con ^
    --hidden-import pywintypes ^
    main.py

if exist "dist\CrosshairStudioPro.exe" (
    echo.
    echo DONE! Your exe is in: dist\CrosshairStudioPro.exe
) else (
    echo.
    echo BUILD FAILED - check the output above for errors
)
pause
