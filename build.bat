@echo off
setlocal enabledelayedexpansion

if not exist ".venv" (
    py -3 -m venv .venv
)

call .venv\Scripts\activate.bat
set EZYM_MAILER_API_BASE_URL=http://15.206.161.73:8765
set EZYM_MAILER_BOOTSTRAP_API=0
set PLAYWRIGHT_BROWSERS_PATH=%CD%\playwright-browsers
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
python -m playwright install chromium

pyinstaller --noconfirm --clean --onefile --windowed --name EzyMailer --hidden-import docx --hidden-import pptx --collect-submodules openpyxl --collect-submodules reportlab main.py

if exist dist\playwright-browsers rmdir /s /q dist\playwright-browsers
robocopy "%PLAYWRIGHT_BROWSERS_PATH%" "dist\playwright-browsers" /MIR >nul
if %ERRORLEVEL% GEQ 8 (
    echo Failed to copy Playwright browser files.
    exit /b 1
)

echo.
echo Build complete. Check dist for EzyMailer.exe and the playwright-browsers folder.
pause
