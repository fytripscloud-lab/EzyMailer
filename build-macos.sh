#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
APP_NAME="EzyMailer"
DIST_DIR="$ROOT_DIR/dist"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
STAGING_DIR="$ROOT_DIR/packaging/macos-dmg"
DMG_NAME="$APP_NAME-macOS.dmg"
DMG_PATH="$DIST_DIR/$DMG_NAME"

export EZYM_MAILER_API_BASE_URL="${EZYM_MAILER_API_BASE_URL:-http://15.206.161.73:8765}"
export EZYM_MAILER_BOOTSTRAP_API="${EZYM_MAILER_BOOTSTRAP_API:-0}"
export PYINSTALLER_CONFIG_DIR="$ROOT_DIR/.pyinstaller"

cleanup_paths() {
  export DIST_DIR ROOT_DIR STAGING_DIR
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
pyinstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "$APP_NAME" \
  --icon "$ROOT_DIR/packaging/macos-dmg/EzyMailer.app/Contents/Resources/icon-windowed.icns" \
  --collect-all PIL \
  --collect-all greenlet \
  --collect-all lxml \
  --collect-all charset_normalizer \
  --hidden-import PIL.Image \
  --hidden-import greenlet._greenlet \
  --exclude-module playwright \
  --exclude-module docx \
  --exclude-module openpyxl \
  --exclude-module reportlab \
  --exclude-module pptx \
  --exclude-module lxml \
  "$ROOT_DIR/main.py"

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

echo "Build complete: $DMG_PATH"
