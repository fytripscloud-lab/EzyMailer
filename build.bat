@echo off
setlocal enabledelayedexpansion
if not exist ".venv" (
    py -3 -m venv .venv
)

call .venv\Scripts\activate.bat
set EZYM_MAILER_API_BASE_URL=http://15.206.161.73:8765
set EZYM_MAILER_BOOTSTRAP_API=0
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name EazyMailer --collect-all PIL --hidden-import PIL.Image --exclude-module playwright --exclude-module docx --exclude-module openpyxl --exclude-module reportlab --exclude-module pptx --exclude-module lxml main.py

echo.
echo Build complete. Check dist for EazyMailer.exe.
