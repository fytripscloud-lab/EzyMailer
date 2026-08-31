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

python -m PyInstaller --noconfirm --clean --onefile --windowed --name EazyMailer --icon packaging\assets\EazyMailer.ico --collect-all PIL --collect-all greenlet --collect-all lxml --collect-all charset_normalizer --collect-all playwright --hidden-import PIL.Image --hidden-import greenlet._greenlet --hidden-import eval_type_backport --add-data "%BROWSER_RUNTIME_DIR%;playwright-browsers" main.py || exit /b 1

if not exist "dist\EazyMailer.exe" (
    echo ERROR: dist\EazyMailer.exe was not generated.
    exit /b 1
)

pyi-archive_viewer -l "dist\EazyMailer.exe" > "dist\EazyMailer-archive.txt" || exit /b 1
findstr /i /c:"playwright-browsers" "dist\EazyMailer-archive.txt" >nul || (
    echo ERROR: Bundled Chromium is missing from dist\EazyMailer.exe.
    exit /b 1
)
del "dist\EazyMailer-archive.txt"
powershell -NoProfile -Command "$hash=(Get-FileHash 'dist\EazyMailer.exe' -Algorithm SHA256).Hash.ToLower(); Set-Content -Encoding ascii 'dist\EazyMailer.exe.sha256' ($hash + '  EazyMailer.exe')" || exit /b 1

echo.
echo Build complete. Check dist for EazyMailer.exe and EazyMailer.exe.sha256.
