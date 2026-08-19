# EzyMailer

EzyMailer now has multiple targets and deployment paths.

## Project Map

- [`PROJECT_TARGETS.md`](/Users/koushikmondal/ezymailer/PROJECT_TARGETS.md) lists the full project split:
  - admin frontend
  - admin/API backend
  - macOS desktop app
  - Windows desktop app
  - MySQL database
  - local SQL database

## Live Deployment

- [`LIVE_DEPLOYMENT_NOTES.md`](/Users/koushikmondal/ezymailer/LIVE_DEPLOYMENT_NOTES.md) documents the Ubuntu-hosted live API/admin frontend setup and the live database rule.
- [`deployment/ubuntu/README.md`](/Users/koushikmondal/ezymailer/deployment/ubuntu/README.md) contains the service and environment file layout for the Ubuntu host.

## Current Local Services

- Admin frontend: `http://127.0.0.1:8780`
- Backend API: `http://127.0.0.1:8765`
- Swagger UI: `http://127.0.0.1:8765/docs`

## Default Local Login

- Username: `admin`
- Password: `admin`

## Desktop App

- Run `main.py` for the packaged desktop application source.
- Build Windows: `build.bat`
- Build macOS: `bash build-macos.sh`
- Desktop builds default to the live API at `http://15.206.161.73:8765` and the dedicated AWS database.
- Windows rebuild flow: pull `main` on the Windows machine, run `build.bat`, and rebuild only the Windows app from that machine.
- Windows first launch downloads the browser runtime into the local cache if Chromium is not already available.

## Notes

- The repo includes dedicated markdown notes for future scope control.
- Live credentials are stored under `server_credentials/` and should not be copied into documentation.
- The hosted backend always uses the dedicated AWS database. Do not point the hosted stack at a local XAMPP/MySQL instance.
