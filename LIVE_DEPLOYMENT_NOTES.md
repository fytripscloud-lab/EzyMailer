# EzyMailer Live Deployment Notes

These notes describe the live production setup and how the repository should be handled going forward.

## Live Hosting Target

- Host OS: Ubuntu
- Services to host on the live machine:
  - Backend API
  - Admin frontend
- The desktop apps are not hosted on the live server.

## Database Layout

- Dedicated live database: production database used by the hosted API and admin frontend
- Local MySQL database: development and desktop build-time database

## Sync Rule

- Before each macOS or Windows build, sync the local MySQL database with the dedicated live database.
- Only new schemas should be applied to the live database.
- Do not overwrite live data unless the change is an intentional schema migration.

## Repository Guidance

- Keep live deployment changes isolated from desktop-only changes.
- Shared backend/API changes may affect:
  - admin frontend
  - macOS desktop app
  - Windows desktop app
- When adding a schema, update both the local and live database paths in a controlled way.

## Credentials Location

- Live OS access key and database credential files are stored in `server_credentials/`.
- Do not commit secrets into code or markdown.
- Reference the credential files locally when configuring the Ubuntu host.

## Current Intent

- Configure the Ubuntu host for:
  - API deployment
  - admin frontend deployment
  - dedicated live database schema management
- Keep desktop packaging connected to the synced local MySQL state.

## Deployment Assets

- Ubuntu setup guide: [`deployment/ubuntu/README.md`](/Users/koushikmondal/ezymailer/deployment/ubuntu/README.md)
- Live schema migration: [`database/migrations/2026-08-18_live_schema_updates.sql`](/Users/koushikmondal/ezymailer/database/migrations/2026-08-18_live_schema_updates.sql)
- Systemd service templates:
  - [`deployment/ubuntu/systemd/ezymailer-backend.service`](/Users/koushikmondal/ezymailer/deployment/ubuntu/systemd/ezymailer-backend.service)
  - [`deployment/ubuntu/systemd/ezymailer-admin.service`](/Users/koushikmondal/ezymailer/deployment/ubuntu/systemd/ezymailer-admin.service)
