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
4. On first launch, the app downloads the browser runtime into the user cache if it is not already available.

The GitHub Actions workflow `.github/workflows/build-windows-exe.yml` runs the same build on Windows x64, installs every package from `requirements.txt`, validates the EXE, and uploads `EzyMailer-Windows-x64` with its SHA-256 checksum.

## macOS build steps

1. Open a terminal in the project root.
2. Run `./build-macos.sh`.
3. Wait for `dist/EzyMailer-macOS.dmg` to be created.

## Output

- One-file executable: `dist\EzyMailer.exe`
- Disk image: `dist/EzyMailer-macOS.dmg`

## Notes

- The app depends on `PySide6`
- macOS packaging creates a `.app` bundle first, then wraps it into a `.dmg`
