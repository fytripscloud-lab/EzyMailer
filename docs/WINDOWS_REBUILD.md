# Windows Rebuild Flow

Use this when working from the Windows machine.

## What to pull

- Pull the latest `main` branch from GitHub.
- Build only the Windows desktop app from Windows.
- Do not copy macOS build artifacts into the repo.

## Build command

1. Open a terminal in the project root on Windows.
2. Run `build.bat`.
3. Wait for `dist\EzyMailer.exe`.

## Runtime behavior

- The Windows EXE uses the live backend API at `http://15.206.161.73:8765/`.
- The Windows EXE uses the dedicated AWS database through the live backend.
- The build downloads the matching Playwright Chromium runtime and embeds it in the one-file EXE.
- At runtime, EzyMailer prefers its embedded Chromium and does not require Google Chrome.

## Notes

- Do not commit build output files.
- If the browser runtime is missing, the loader will show an auto-configuring message during the first launch.
