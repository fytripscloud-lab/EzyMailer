# Ubuntu Live Deployment

This folder contains the live hosting setup for the production Ubuntu host.

## Targets

- Backend API
- Admin frontend

## Environment file

Create an environment file on the server, for example:

`/etc/ezymailer/ezymailer.env`

Use the template in `env.example` as the base and fill in the live values from `server_credentials/`.

## Services

- `ezymailer-backend.service` runs the shared API
- `ezymailer-admin.service` runs the browser-based admin frontend

EazyValidator (`EmailValidator/`) is **not** hosted here - it's bundled straight into the desktop app's
`.dmg`/`.exe` (see `build-macos.sh`/`build.bat` and `LIVE_DEPLOYMENT_NOTES.md`) and runs locally on
`127.0.0.1:8766` inside the app itself. `ezymailer-validator-backend.service` /
`ezymailer-validator-frontend.service` below are kept only as a reference for that earlier approach, stopped
and disabled as of 2026-11-04.

## Database sync

- Apply `database/migrations/2026-08-18_live_schema_updates.sql` to the dedicated live database when new schema fields are added.
- Keep the migration additive. Do not drop live columns or tables unless a backward-compatible plan exists.
- The hosted API and hosted admin frontend must always point to the dedicated live database, never the local development database.

## Suggested deployment flow

1. Provision Ubuntu.
2. Install Python, system packages, and the project virtual environment.
3. Create the environment file under `/etc/ezymailer/`.
4. Apply the live schema migration to the dedicated database.
5. Enable and start the backend and admin systemd services.
