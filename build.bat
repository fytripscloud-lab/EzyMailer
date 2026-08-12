@echo off
setlocal enabledelayedexpansion

if not exist ".venv" (
    py -3 -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --noconfirm --clean --onefile --windowed --name EzyMailer main.py

echo.
echo Build complete. Check the dist folder for EzyMailer.exe
pause
