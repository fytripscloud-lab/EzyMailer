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

python -m PyInstaller --noconfirm --clean --onefile --windowed --name EazyMailer --icon packaging\assets\EazyMailer.ico --collect-all PIL --collect-all greenlet --collect-all lxml --collect-all charset_normalizer --collect-all playwright --hidden-import PIL.Image --hidden-import greenlet._greenlet --hidden-import eval_type_backport main.py || exit /b 1

if not exist "dist\EazyMailer.exe" (
    echo ERROR: dist\EazyMailer.exe was not generated.
    exit /b 1
)

REM Chromium is no longer bundled in the exe -- it downloads on first login
REM as part of the app's runtime-dependency archive (see
REM .github/workflows/publish-dependencies.yml) and is cached under
REM %USERPROFILE%\.ezymailer instead.
powershell -NoProfile -Command "$hash=(Get-FileHash 'dist\EazyMailer.exe' -Algorithm SHA256).Hash.ToLower(); Set-Content -Encoding ascii 'dist\EazyMailer.exe.sha256' ($hash + '  EazyMailer.exe')" || exit /b 1

echo.
echo Build complete. Check dist for EazyMailer.exe and EazyMailer.exe.sha256.
