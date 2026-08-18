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

## Database sync

- Apply `database/migrations/2026-08-18_live_schema_updates.sql` to the dedicated live database when new schema fields are added.
- Keep the migration additive. Do not drop live columns or tables unless a backward-compatible plan exists.

## Suggested deployment flow

1. Provision Ubuntu.
2. Install Python, system packages, and the project virtual environment.
3. Create the environment file under `/etc/ezymailer/`.
4. Apply the live schema migration to the dedicated database.
5. Enable and start the backend and admin systemd services.
