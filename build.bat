@echo off
setlocal enabledelayedexpansion
if not exist ".venv" (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
set EZYM_MAILER_API_BASE_URL=http://15.206.161.73:8765
set EZYM_MAILER_BOOTSTRAP_API=0
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name EazyMailer --icon packaging\assets\EazyMailer.ico --collect-all PIL --collect-all greenlet --collect-all lxml --collect-all charset_normalizer --hidden-import PIL.Image --hidden-import greenlet._greenlet --exclude-module playwright main.py

echo.
echo Build complete. Check dist for EazyMailer.exe.
