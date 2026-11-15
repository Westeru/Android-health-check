@echo off
title Build AndroidHealthDoctor.exe (Standalone Portable App)
cd /d "%~dp0"
echo Installing/Checking PyInstaller...
pip install pyinstaller -q
python build_exe.py
pause
