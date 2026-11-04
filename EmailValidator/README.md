# Bulk Email Validator

A standalone, production-ready bulk email validation application. Upload a spreadsheet of email addresses, validate every address through a real syntax/DNS/MX/SMTP pipeline, watch live progress, review results in a searchable/filterable table, and export Excel/CSV/PDF reports. No login, no database, no cloud storage — everything lives on the local filesystem under `backend/imported/`.

```
project/
├── backend/   FastAPI validation API (Python)
├── frontend/  Next.js + MUI dashboard (TypeScript)
└── README.md
```

## 1. Features implemented

**Upload** — drag-and-drop or browse for `.xlsx` / `.xls` / `.csv`; shows filename, size, and detected record count; auto-detects the email column (header aliases, then content sniffing against a sample of rows) with manual override when detection fails or is ambiguous; remove-file button deletes the job on the backend.

**Validation progress** — polling every ~1.5s (`/progress/{job_id}`) showing total/processed/remaining, valid/invalid/risky/unknown counts, percent complete, emails/sec, and ETA; a Cancel button requests graceful cancellation (finishes the in-flight batch, keeps partial results).

**Results table** — MUI DataGrid with server-side pagination, a search box (debounced), and filter chips (All/Valid/Invalid/Risky/Unknown/Disposable). Columns: Row No., Email, Syntax, Domain, MX Record, SMTP, Disposable, Free Provider, Role Based, Catch-All, Final Status — plus every original spreadsheet column, preserved alongside the validation results.

**Export** — Excel (multi-sheet: All/Valid/Invalid/Risky/Unknown Results, each keeping original columns), CSV, and a PDF summary report (ReportLab) with a status-distribution pie chart.

**Summary report** — total/unique/duplicate counts, per-status counts, disposable/free-provider/role-based counts, success percentage, validation duration, and MUI X Charts visualizations (status pie chart, risk-signal bar chart).

### Validation engine

Per email: syntax (`email-validator`) → domain existence + MX lookup (`dnspython`, cached per domain with a TTL and request coalescing so duplicate domains never re-query DNS) → disposable / free-provider / role-based lookups (bundled static lists) → SMTP `RCPT TO` probe (`aiosmtplib`; connects, `EHLO`/`MAIL FROM`/`RCPT TO`, then `QUIT` — **never** sends `DATA`, i.e. never sends an actual email) → catch-all detection (one cached random-address probe per domain).

**Final status rule** (never infers a valid mailbox from MX alone, returns `unknown` when inconclusive):
- `invalid` — bad syntax, nonexistent domain, no MX, or an SMTP hard-reject (55x)
- `risky` — disposable domain, role-based local part, or a catch-all domain (even if SMTP accepted)
- `valid` — syntax/domain/MX ok, SMTP accepted, not disposable, not catch-all
- `unknown` — SMTP inconclusive, blocked, or timed out, with no other invalid/risk signal

### Performance & reliability

Per-domain DNS/catch-all caching and lock-coalescing; configurable `asyncio.Semaphore`s bound DNS and SMTP concurrency independently; files are streamed and processed in configurable batches (never holding the whole result set in memory); results are appended to `results.jsonl` incrementally so progress/cancellation are always consistent with what's on disk; one retry on transient SMTP connection failures; graceful cancellation checked between batches.

### Security

Job IDs are random UUIDs and the only values ever used to build filesystem paths; uploaded filenames are sanitized and used only for display/`Content-Disposition`; uploaded content is magic-byte sniffed and checked against the claimed extension (rejects disguised files); configurable max upload size and max row count; upload/start endpoints are rate-limited (`slowapi`); before connecting to any resolved MX host for the SMTP check, the resolved IP is checked against private/loopback/link-local/reserved ranges (SSRF / DNS-rebinding guard); CORS is restricted to the configured frontend origin; a background task deletes job directories past a configurable retention window.

## 2. Backend API

Base path `/api/v1/bulk-validator`:

| Method & path | Purpose |
|---|---|
| `POST /upload` | Upload a file, auto-detect the email column |
| `POST /start/{job_id}` | Start validation (optional `email_column` / `sheet_name` override) |
| `GET /progress/{job_id}` | Poll live progress |
| `GET /results/{job_id}` | Paginated, filterable, searchable results |
| `GET /report/{job_id}` | Summary report JSON |
| `GET /export/{job_id}?format=xlsx\|csv\|pdf` | Download a generated export |
| `POST /cancel/{job_id}` | Request graceful cancellation |
| `DELETE /job/{job_id}` | Delete all files/metadata for a job |

## 3. Dependencies

**Backend** (`backend/requirements.txt`): fastapi, uvicorn, python-multipart, pydantic / pydantic-settings, pandas, openpyxl, xlrd, email-validator, dnspython, aiosmtplib, reportlab, slowapi, pytest / pytest-asyncio / httpx (tests).

**Frontend** (`frontend/package.json`): next, react, @mui/material + @mui/icons-material + @mui/x-data-grid + @mui/x-charts + @mui/material-nextjs, @emotion/*, react-dropzone, axios; jest, @testing-library/react + jest-dom + user-event (tests).

## 4. Running locally

**Backend**

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # adjust as needed
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open http://localhost:3000. The backend's interactive API docs are at http://localhost:8000/docs.

> **SMTP checks and port 25**: mailbox verification (`RCPT TO`) and catch-all detection need outbound TCP/25. Most cloud PaaS providers (Heroku, AWS, GCP, etc.) block this by default — in that case SMTP checks will consistently return `unknown`, which the app treats correctly as inconclusive rather than failing. Run on a machine/VPS with open outbound port 25 for full SMTP verification, or set `ENABLE_SMTP_CHECK=false` to skip it entirely and rely on syntax/DNS/MX/disposable/role checks only. The frontend's **System Status** panel (shown at the top of the dashboard) checks and reports whether port 25 is actually reachable from the backend, so you don't have to guess.
>
> **Even with port 25 open**, expect some irreducible `unknown` rate — SMTP verification is inherently imperfect:
> - **Greylisting**: many servers temporarily 4xx-reject first-time senders and expect a retry minutes later; `SMTP_RETRIES` won't out-wait that.
> - **Sender reputation**: a fresh IP with no PTR (reverse DNS) record, SPF, or sending history gets soft-rejected by reputation-sensitive providers (Microsoft/Outlook especially). Set up a PTR record pointing back at your VPS's hostname, and make `SMTP_HELO_DOMAIN` / `SMTP_FROM_ADDRESS` (in `.env`) a real domain you control with a matching SPF record — mismatched or unresolvable values get many servers to reject the probe regardless of whether the recipient mailbox is real.
> - **Rate limiting**: Gmail/Yahoo/Outlook throttle RCPT-only connections aggressively from one IP. Keep `SMTP_CONCURRENCY` conservative (default `5`) and watch the per-domain `unknown` rate before raising it.
> - **Reputation decay over time**: an IP used purely for verification probes (no real mail ever sent) can itself get flagged by some providers over time — monitor your results rather than assuming port-25-open means permanently reliable verification.

## 5. Deployment notes

**Production path: bundled into the EzyMailer desktop app, not hosted separately.** `next.config.ts` sets
`output: "export"`; `EmailValidator/backend/app/main.py` mounts that static export (`frontend/out/`) at `/`
via `StaticFiles`, so one process serves the whole thing. PyInstaller bundles `EmailValidator/backend/app`
(via `--paths`) and `frontend/out` (via `--add-data ...:validator_frontend`) straight into the `.dmg`/`.exe`
(`build-macos.sh` / `build.bat`), and `main.py`'s `ensure_validator_server()` starts it on `127.0.0.1:8766`
the first time the user clicks "Mail Validator" — same pattern as `ensure_api_server()` for the main backend.
Auth needs no setup: it reads `EZYM_MAILER_JWT_SECRET` from the same process environment as EzyMailer's own
backend, so a token from EzyMailer's `/api/login` just works here too.

Run `npm run build` (frontend) before every `./build-macos.sh` / `build.bat` — the build scripts fail fast if
`frontend/out/` is missing.

### Standalone/dev deployment (not currently used in production)

- Both services are stateless aside from the `backend/imported/` filesystem tree — back that up or treat it as ephemeral per your retention policy (`JOB_RETENTION_HOURS`, `CLEANUP_INTERVAL_MINUTES` in `.env`).
- Run the backend behind a process manager (systemd, pm2, supervisord) with `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1` — keep it to one worker process since job state (running-task tracking, cancellation flags) is in-process memory plus the filesystem; scaling to multiple workers/machines would need that moved to a shared store.
- With `output: "export"`, `next start` no longer works for the frontend — serve `frontend/out/` as static files (the bundled path above already does this via the backend) or revert `output: "export"` in `next.config.ts` if running it as its own Node service again.
- Put a reverse proxy (nginx/Caddy) in front for TLS; no proxy-specific config is required since progress updates use plain HTTP polling.

## 6. Test results

**Backend — 59/59 passed** (`cd backend && source .venv/bin/activate && pytest -q`): file parsing & column auto-detection, every validation check (syntax, disposable, free-provider, role-based, DNS/MX caching + NXDOMAIN/timeout handling, SMTP accept/reject/unknown/retry, catch-all detection — DNS/SMTP mocked for determinism), the final-status decision table, job-store persistence & filtered/paginated queries, export (xlsx sheets/csv) and PDF report generation, retention-based cleanup, and full API integration flows (upload → start → progress → results → report → export → cancel → delete), including manual column selection and the pre-completion 409 cases.

**Frontend — 17/17 passed** (`cd frontend && npm test`): the upload component (success, failed auto-detect, manual column start, remove/delete, upload error), the results table (load, filter-chip refetch, debounced search, error state), the polling hook (immediate + interval ticks, inactive, cleanup on unmount), and the API error-message helper. TypeScript (`npx tsc --noEmit`) and ESLint (`npm run lint`) are both clean.

**Manual end-to-end verification** (performed against the real running servers, not mocked): uploaded a real CSV with a mix of a free-provider address, a disposable+role-based address, a malformed address, and a role-based address at a normal domain; started validation and polled progress to completion; confirmed DNS/MX lookups succeeded for real; confirmed that on this network outbound SMTP (port 25) is blocked, and the engine correctly reported `unknown` rather than ever claiming those mailboxes were verified; downloaded and verified the magic bytes/sheet structure of the `.xlsx`, `.csv`, and `.pdf` exports; confirmed `DELETE /job/{job_id}` removes the upload/processing/export/report directories from disk (subsequent requests 404); confirmed the retention-based cleanup sweep removes a back-dated job directory.

**Not verified**: interactive UI behavior in a real browser (drag-and-drop, button clicks, DataGrid rendering) — no browser automation tool was available in this environment. The dev server was confirmed to render the expected markup via an HTTP request, and all interactive logic is covered by the Jest component tests above, but a manual click-through in an actual browser is recommended before considering the frontend fully verified.
