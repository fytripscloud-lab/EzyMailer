# EzyMailer Project Targets

This repository has multiple separate deliverables. Keep work scoped to the correct target.

## Projects

1. Frontend for admin
2. Backend/API for admin and desktop app support on Mac and Windows
3. Desktop app for macOS
4. Desktop app for Windows

## Databases

5. MySQL database
6. Local SQL database

## Scope Rule

- Update only the project that the request applies to.
- Do not assume changes for one target should automatically apply to the others.
- If a change affects shared behavior, note which targets are impacted before editing.

## Current Usage

- Admin frontend: browser-based admin portal
- Admin backend/API: shared API for admin portal and desktop apps
- Desktop macOS app: local packaged app for Apple systems
- Desktop Windows app: local packaged app for Windows systems
- MySQL database: dedicated AWS live database used by the hosted backend and the app builds
- Local SQL database: local app-side state and cache storage

## Live Deployment

- See [`LIVE_DEPLOYMENT_NOTES.md`](/Users/koushikmondal/ezymailer/LIVE_DEPLOYMENT_NOTES.md) for the Ubuntu-hosted live API/admin frontend setup and the database sync rule.
