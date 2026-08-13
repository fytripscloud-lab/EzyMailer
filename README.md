# EzyMailer

Desktop email automation app in Python.

## Current milestone

- Login page with default credentials
- Modern dashboard shell with sidebar, top bar, activity log, and tabbed workspace
- Complete design pass for Data, Subject + Body, Content, Settings, Campaign, and Tags
- Project memory and update logs in Markdown

## Default login

- Username: `admin`
- Password: `admin`

## Local API

- The app starts a localhost login API automatically
- Database name: `ezymailer`
- User table: `user_db`
- Seed user: `admin / admin`
- API base URL: `http://127.0.0.1:8765`
- Swagger UI: `http://127.0.0.1:8765/docs`
- JWT bearer tokens are issued from the login endpoint

## Run

Install dependencies, then launch `main.py`.

## Build EXE

Run `build.bat` on Windows to create `dist\\EzyMailer.exe`.

## Build DMG

Run `./build-macos.sh` on macOS to create `dist/EzyMailer-macOS.dmg`.

## Next milestone

- Gmail OAuth login
- Session launch/stop/reset behavior
- Database, subject, content, settings, sender, and tag workflows
- Packaging into Windows `.exe` and macOS `.dmg`
