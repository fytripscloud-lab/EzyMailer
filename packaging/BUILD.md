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
4. Keep the generated `dist\playwright-browsers` folder beside the EXE so the bundled browser runtime is available at launch.

## macOS build steps

1. Open a terminal in the project root.
2. Run `./build-macos.sh`.
3. Wait for `dist/EzyMailer-macOS.dmg` to be created.

## Output

- One-file executable: `dist\EzyMailer.exe`
- Playwright browser runtime folder: `dist\playwright-browsers`
- Disk image: `dist/EzyMailer-macOS.dmg`

## Notes

- The app depends on `PySide6`
- macOS packaging creates a `.app` bundle first, then wraps it into a `.dmg`
