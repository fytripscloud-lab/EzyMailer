#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
APP_NAME="EzyMailer"
DIST_DIR="$ROOT_DIR/dist"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
STAGING_DIR="$ROOT_DIR/packaging/macos-dmg"
BROWSER_RUNTIME_DIR="$ROOT_DIR/packaging/browser-runtime-macos"
DMG_NAME="$APP_NAME-macOS.dmg"
DMG_PATH="$DIST_DIR/$DMG_NAME"

export EZYM_MAILER_API_BASE_URL="${EZYM_MAILER_API_BASE_URL:-http://15.206.161.73:8765}"
export EZYM_MAILER_BOOTSTRAP_API="${EZYM_MAILER_BOOTSTRAP_API:-0}"
export PYINSTALLER_CONFIG_DIR="$ROOT_DIR/.pyinstaller"

cleanup_paths() {
  export BROWSER_RUNTIME_DIR DIST_DIR ROOT_DIR STAGING_DIR
python3 - <<'PY'
import os
from pathlib import Path
import shutil
import subprocess

paths = [
    Path(os.environ["ROOT_DIR"]) / "build",
    Path(os.environ["DIST_DIR"]) / "EzyMailer.app",
    Path(os.environ["DIST_DIR"]) / "EzyMailer-macOS.dmg",
    Path(os.environ["STAGING_DIR"]),
    Path(os.environ["BROWSER_RUNTIME_DIR"]),
]
for path in paths:
    if path.exists():
        if path.is_dir():
            subprocess.run(["/bin/rm", "-rf", str(path)], check=True)
        else:
            path.unlink()
PY
}

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
pip install -r "$ROOT_DIR/requirements.txt"
pip install pyinstaller

cleanup_paths
mkdir -p "$PYINSTALLER_CONFIG_DIR"
mkdir -p "$BROWSER_RUNTIME_DIR"
PLAYWRIGHT_BROWSERS_PATH="$BROWSER_RUNTIME_DIR" python -m playwright install --no-shell chromium

if ! find "$BROWSER_RUNTIME_DIR" -type f -path '*chromium-*/*Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing' -perm +111 -print -quit | grep -q .; then
  echo "ERROR: Playwright Chromium was not prepared for the macOS package."
  exit 1
fi

pyinstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "$APP_NAME" \
  --icon "$ROOT_DIR/packaging/assets/EazyMailer.icns" \
  --collect-all PIL \
  --collect-all greenlet \
  --collect-all lxml \
  --collect-all charset_normalizer \
  --hidden-import PIL.Image \
  --hidden-import greenlet._greenlet \
  --hidden-import eval_type_backport \
  --collect-all playwright \
  "$ROOT_DIR/main.py"

mkdir -p "$APP_BUNDLE/Contents/Resources/playwright-browsers"
ditto "$BROWSER_RUNTIME_DIR" "$APP_BUNDLE/Contents/Resources/playwright-browsers"

if ! find "$APP_BUNDLE/Contents" -type f -path '*playwright-browsers/chromium-*/*Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing' -perm +111 -print -quit | grep -q .; then
  echo "ERROR: Bundled Chromium is missing from $APP_BUNDLE."
  exit 1
fi

# Chromium is a nested signed app. Copy it after PyInstaller collection, then
# seal the complete EzyMailer bundle so Gatekeeper sees a consistent package.
codesign --force --deep --sign - "$APP_BUNDLE"
codesign --verify --deep --strict "$APP_BUNDLE"

mkdir -p "$STAGING_DIR"
cp -cR "$APP_BUNDLE" "$STAGING_DIR/"
ln -s /Applications "$STAGING_DIR/Applications"

export DMG_PATH
python3 - <<'PY'
import os
from pathlib import Path

path = Path(os.environ["DMG_PATH"])
if path.exists():
    path.unlink()
PY
hdiutil create \
  -volname "$APP_NAME" \
  -srcfolder "$STAGING_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

(cd "$DIST_DIR" && shasum -a 256 "$DMG_NAME" > "$DMG_NAME.sha256")
echo "Build complete: $DMG_PATH and $DMG_PATH.sha256"
