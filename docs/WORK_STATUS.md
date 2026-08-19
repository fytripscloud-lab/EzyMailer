# EzyMailer Work Status

This file tracks what is already implemented and what still needs work.
Use this as the source of truth when asking for pending items.

## How to use this tracker

- Ask for `pending work` to get the items still open.
- Ask for `done work` to get the completed items.
- Ask for a specific feature name to get a focused status update.

## Completed

### Authentication and Access Control

- Admin login is implemented through the backend API.
- Login uses device fingerprint and validity checks.
- Login now prompts when the account is active on another device and supports forced logout of the previous device.
- Admin-only access is enforced on the backend for admin routes.
- User activation, deactivation, password reset, and device reset APIs are implemented.

### Admin Frontend

- Browser-based admin portal is implemented.
- Overview dashboard exists with charts and summary cards.
- Users page exists with search, filter, pagination, and row actions.
- Validity expired page exists.
- Activity page exists.
- Login history page exists.
- Full user detail modal exists.

### Database and Backend

- Dedicated MySQL schema exists for the project.
- Live schema migration for user validity and device binding exists.
- Tables exist for users, login history, activity log, browser sessions, settings, content library, tags, and customer variables.
- Backend APIs exist for users, activity, login history, browser sessions, settings, tags, and customer variables.

### Tags and Variables

- Dynamic tags are implemented.
- Manual custom tags are implemented.
- Customer variables save, refresh, list, and delete flows are implemented.
- Tag and variable data are persisted through backend APIs and local storage.

### Campaign Flow

- Gmail compose automation is implemented with Playwright.
- Subject, body, attachment content, and file name support tag replacement.
- HTML-to-JPG rendering exists.
- JPG-to-output-format conversion exists.
- Attachment formats supported include PDF, DOCX, XLSX, XLTX, PPTX, and PPSX.
- Campaign start now validates required fields before sending.
- Reset All clears the campaign form back to defaults.
- Recipient validation state is tracked locally so sending stays disabled until the list is validated.

### Desktop App State

- Browser session tracking is implemented.
- Activity logging is implemented.
- Sending settings UI is implemented and persisted.
- AI assistant UI exists.
- Campaign data, subject/body, and attachment content remain local-state driven.
- Tags and user preferences continue to sync through the dedicated database path.

## Partial

### Customer Email Repository

- Recipient email entry and validation exist in the desktop app.
- A dedicated backend recipient database and API are not yet clearly implemented as a first-class server feature.

### AI Assistant

- The AI assistant UI can connect to providers from the desktop app.
- Backend persistence for provider, API key, model, and status is not yet implemented as a dedicated API/DB feature.

### Sending Settings Enforcement

- Sending settings are available in the UI and saved.
- Full backend enforcement for every sending rule is not yet split into a dedicated server service.

### Campaign UX Gaps

- Preview before send is still not a first-class campaign step.
- Pause, resume, and cancel controls for an in-flight campaign are still pending.
- Dynamic per-campaign tag generation and uniqueness enforcement still need review.

### Audit Coverage

- Activity logging exists.
- Full server-side audit coverage for every desktop action is still incomplete.

## Pending

### Backend/API Gaps

- Dedicated recipient list database and CRUD API.
- AI assistant configuration storage API and database support.
- Proxy settings backend support.
- Startup URL backend support.
- Dedicated campaign orchestration API if campaign execution must be server-managed.

### Data Pipeline Gaps

- Central CSV import pipeline for recipient management.
- Server-side validation/count pipeline for uploaded recipient data.
- Stronger persistence for recipient/domain filter workflows.

### Operational Gaps

- Final production hardening for hosted deployments if any remaining endpoint or port exposure issues exist.
- Any remaining schema additions should be applied as additive migrations only.

## Notes

- The hosted backend and hosted admin frontend must always target the dedicated live AWS MySQL database.
- Before any `.dmg` or `.exe` build, update and verify the live backend, admin frontend, and schema changes first.
- The rebuild artifact must use the live API and live database, not the local development backend.
- For Windows rebuilds, pull the latest `main` branch on Windows and run `build.bat` there only.
- Do not place secrets in this file.
