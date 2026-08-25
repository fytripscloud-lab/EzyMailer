@echo off
setlocal enabledelayedexpansion
if not exist ".venv" (
    python -m venv .venv || exit /b 1
)

call .venv\Scripts\activate.bat || exit /b 1
set EZYM_MAILER_API_BASE_URL=http://15.206.161.73:8765
set EZYM_MAILER_BOOTSTRAP_API=0
python -m pip install --upgrade pip || exit /b 1
python -m pip install --requirement requirements.txt || exit /b 1
python -m pip install pyinstaller || exit /b 1
python -m PyInstaller --noconfirm --clean --onefile --windowed --name EazyMailer --icon packaging\assets\EazyMailer.ico --collect-all PIL --collect-all greenlet --collect-all lxml --collect-all charset_normalizer --hidden-import PIL.Image --hidden-import greenlet._greenlet --exclude-module playwright main.py || exit /b 1

if not exist "dist\EazyMailer.exe" (
    echo ERROR: dist\EazyMailer.exe was not generated.
    exit /b 1
)

echo.
echo Build complete. Check dist for EazyMailer.exe.
