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
- `ezymailer-validator-backend.service` runs EazyValidator's FastAPI backend (port 8766), isolated under
  `/opt/ezymailer-validator/backend` - independent of the services above, so it never touches their
  venv/process. Requires its own env file at `/etc/ezymailer-validator/backend.env` with
  `EZYM_MAILER_JWT_SECRET` set to the **same value** as `/etc/ezymailer/ezymailer.env`, so a token issued by
  `ezymailer-backend`'s `/api/login` is also accepted here - that's what lets the desktop app's "Mail
  Validator" button open the page already signed in.
- `ezymailer-validator-frontend.service` runs EazyValidator's Next.js frontend (port 8781) via `npm start`,
  built with `NEXT_PUBLIC_API_URL` pointed at port 8766. Rebuild (`npm run build`) after any frontend change.

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
