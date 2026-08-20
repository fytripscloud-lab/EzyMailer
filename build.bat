@echo off
setlocal enabledelayedexpansion
set PLAYWRIGHT_BROWSERS_PATH=%~dp0packaging\playwright-browsers

if not exist ".venv" (
    py -3 -m venv .venv
)

call .venv\Scripts\activate.bat
set EZYM_MAILER_API_BASE_URL=http://15.206.161.73:8765
set EZYM_MAILER_BOOTSTRAP_API=0
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
python -m playwright install chromium

pyinstaller --noconfirm --clean --onefile --windowed --name EzyMailer --hidden-import docx --hidden-import pptx --collect-submodules openpyxl --collect-submodules reportlab main.py

if exist "dist\playwright-browsers" rmdir /S /Q "dist\playwright-browsers"
xcopy "%PLAYWRIGHT_BROWSERS_PATH%" "dist\playwright-browsers\" /E /I /Y /Q

echo.
echo Build complete. Check dist for EzyMailer.exe.
pause
