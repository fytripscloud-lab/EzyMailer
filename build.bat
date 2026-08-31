@echo off
setlocal enabledelayedexpansion
if not exist ".venv" (
    python -m venv .venv || exit /b 1
)

call .venv\Scripts\activate.bat || exit /b 1
set EZYM_MAILER_API_BASE_URL=http://15.206.161.73:8765
set EZYM_MAILER_BOOTSTRAP_API=0
set BROWSER_RUNTIME_DIR=%CD%\packaging\browser-runtime-windows
python -m pip install --upgrade pip || exit /b 1
python -m pip install --requirement requirements.txt || exit /b 1
python -m pip install pyinstaller || exit /b 1

if exist "%BROWSER_RUNTIME_DIR%" rmdir /s /q "%BROWSER_RUNTIME_DIR%"
mkdir "%BROWSER_RUNTIME_DIR%" || exit /b 1
set PLAYWRIGHT_BROWSERS_PATH=%BROWSER_RUNTIME_DIR%
python -m playwright install --no-shell chromium || exit /b 1

set CHROMIUM_EXE=
for /r "%BROWSER_RUNTIME_DIR%" %%F in (chrome.exe) do (
    echo %%F | findstr /i /c:"\chromium-" >nul && set CHROMIUM_EXE=%%F
)
if not defined CHROMIUM_EXE (
    echo ERROR: Playwright Chromium was not prepared for the Windows package.
    exit /b 1
)

python -m PyInstaller --noconfirm --clean --onefile --windowed --name EzyMailer --icon packaging\assets\EzyMailer.ico --collect-all PIL --collect-all greenlet --collect-all lxml --collect-all charset_normalizer --collect-all playwright --hidden-import PIL.Image --hidden-import greenlet._greenlet --hidden-import eval_type_backport --add-data "%BROWSER_RUNTIME_DIR%;playwright-browsers" main.py || exit /b 1

if not exist "dist\EzyMailer.exe" (
    echo ERROR: dist\EzyMailer.exe was not generated.
    exit /b 1
)

pyi-archive_viewer -l "dist\EzyMailer.exe" > "dist\EzyMailer-archive.txt" || exit /b 1
findstr /i /c:"playwright-browsers" "dist\EzyMailer-archive.txt" >nul || (
    echo ERROR: Bundled Chromium is missing from dist\EzyMailer.exe.
    exit /b 1
)
del "dist\EzyMailer-archive.txt"
powershell -NoProfile -Command "$hash=(Get-FileHash 'dist\EzyMailer.exe' -Algorithm SHA256).Hash.ToLower(); Set-Content -Encoding ascii 'dist\EzyMailer.exe.sha256' ($hash + '  EzyMailer.exe')" || exit /b 1

echo.
echo Build complete. Check dist for EzyMailer.exe and EzyMailer.exe.sha256.
