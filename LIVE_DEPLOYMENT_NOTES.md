# EzyMailer Live Deployment Notes

These notes describe the live production setup and how the repository should be handled going forward.

## Live Hosting Target

- Host OS: Ubuntu
- Live host private IP: `172.26.1.104`
- Live host public IP: `15.206.161.73`
- Services to host on the live machine:
  - Backend API
  - Admin frontend
- The desktop apps are not hosted on the live server.

## Database Layout

- Dedicated live database: production database used by the hosted API, admin frontend, and development builds
- Local SQL database: local app-side state and cache storage only

## Sync Rule

- Before each macOS or Windows build, use the dedicated live database as the source of truth for schema and application data.
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
- Keep desktop packaging connected to the dedicated live database and local SQL state where required.

## Deployment Assets

- Ubuntu setup guide: [`deployment/ubuntu/README.md`](/Users/koushikmondal/ezymailer/deployment/ubuntu/README.md)
- Live schema migration: [`database/migrations/2026-08-18_live_schema_updates.sql`](/Users/koushikmondal/ezymailer/database/migrations/2026-08-18_live_schema_updates.sql)
- Systemd service templates:
  - [`deployment/ubuntu/systemd/ezymailer-backend.service`](/Users/koushikmondal/ezymailer/deployment/ubuntu/systemd/ezymailer-backend.service)
  - [`deployment/ubuntu/systemd/ezymailer-admin.service`](/Users/koushikmondal/ezymailer/deployment/ubuntu/systemd/ezymailer-admin.service)

## Verified Live State

- Backend API service is running on `0.0.0.0:8765`
- Admin frontend service is running on `0.0.0.0:8780`
- Local health checks on the Ubuntu host are responding:
  - `http://127.0.0.1:8765/api/health`
  - `http://127.0.0.1:8780/health`
- The remaining blocker for browser access is AWS network exposure, not the app process itself.
- The instance must allow inbound traffic to the live ports from the internet or from the intended proxy / load balancer.

## Required AWS Inbound Access

- Open the following ports in the AWS security group or load balancer rule set for the live instance:
  - `8765` for the backend API
  - `8780` for the admin frontend
- If using a public web entrypoint, place Nginx or a load balancer in front and map standard HTTP/HTTPS traffic to the internal app ports.

## Hosted Database Rule

- The hosted backend and hosted admin frontend must always use the dedicated live database.
- The hosted admin frontend talks only to the backend API.
- The hosted backend must not point to the local development database when deployed on Ubuntu.
- Use the live database credentials from `server_credentials/` only for the hosted environment.
