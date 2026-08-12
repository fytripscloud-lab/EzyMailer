# Windows EXE Build

## Purpose

Build the desktop app into a Windows executable using PyInstaller.

## Prerequisites

- Python 3.10+ installed on Windows
- Internet access for first-time dependency installation

## Build steps

1. Open a terminal in the project root.
2. Run `build.bat`.
3. Wait for `dist\EazyMailer.exe` to be created.

## Output

- One-file executable: `dist\EazyMailer.exe`

## Notes

- The app currently depends on `PySide6`
- The current environment does not include Python, so the executable cannot be produced here directly
