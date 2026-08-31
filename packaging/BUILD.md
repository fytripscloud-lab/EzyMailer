# Build Packages

## Purpose

Build the desktop app into platform-specific packages using PyInstaller.

## Prerequisites

- Python 3.10+ installed on the target platform
- Internet access for first-time dependency installation

## Windows build steps

1. Open a terminal in the project root.
2. Run `build.bat`.
3. Wait for `dist\EzyMailer.exe` to be created.
4. Chromium is downloaded at build time and embedded in `EzyMailer.exe`.

The GitHub Actions workflow `.github/workflows/build-windows-exe.yml` runs the same build on Windows x64, installs every package from `requirements.txt`, validates the EXE, and uploads `EzyMailer-Windows-x64` with its SHA-256 checksum.

## macOS build steps

1. Open a terminal in the project root.
2. Run `./build-macos.sh`.
3. Wait for `dist/EzyMailer-macOS.dmg` to be created.

## Output

- One-file executable: `dist\EzyMailer.exe`
- Windows checksum: `dist\EzyMailer.exe.sha256`
- Disk image: `dist/EzyMailer-macOS.dmg`

## Notes

- Both platform builds include the Playwright package and the matching Chromium runtime.
- The app prefers bundled Chromium and only uses a user-cache or installed browser as fallback.
- The app depends on `PySide6`.
- macOS packaging creates a `.app` bundle first, embeds Chromium, then wraps it into a `.dmg`.
- PyInstaller must run on the target operating system; use Windows or the Windows GitHub Actions runner for the EXE.
