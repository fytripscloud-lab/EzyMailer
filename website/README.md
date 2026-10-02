# EzyMailer Website

Marketing site for EzyMailer — React 19 + Vite + Material UI (MUI). Frontend only.

## Run

```bash
npm install
npm run dev       # http://localhost:5173
npm run build     # static output in dist/
npm run preview   # serve the production build
```

## Configure before going live

Everything release- or deployment-specific is in `src/config/site.js`:

- `downloads.windows.url` / `downloads.mac.url` — where the installers are hosted.
  Either upload them somewhere (S3, GitHub Releases…) and paste the URLs, or copy
  them into `public/downloads/` (git-ignored) to serve them from the same host.
- `version`, `releaseDate`, file `size` and `sha256` — update for every release
  (checksums come from `dist/*.sha256` after `build-macos.sh` / `build.bat`).
- `telegramUrl` — target of the floating chat button and the Contact page chat card.
- Contact emails, company name, legal jurisdiction and effective date.

## Structure

- `src/pages/` — Home, Features, Download, FAQ, About, Contact, 404
- `src/pages/legal/` — Terms, Privacy, Cookies, Acceptable Use, EULA, Disclaimer
- `src/pages/auth/` — Login, Register, Forgot password
- `src/pages/account/` — signed-in portal: Dashboard, Licence (with extend), Updates & news,
  Profile & security (change password), Login logs, Renewal history

## Account area is design only

Login/Register just open `/account`; nothing is authenticated or saved. Every value
shown in the portal comes from `src/data/mockAccount.js` (sample user, licence,
plans and prices, logs, renewals, updates). Replace those imports with API calls
when the backend is ready.
- `src/data/` — feature list, FAQ and legal text (edit content here, not in pages)
- `src/components/` — layout, navbar, footer, animated app mockup, shared UI
- `src/theme.js` — MUI theme and neon colour tokens

## Hosting

It is a single-page app using client-side routes (`/features`, `/terms`, …), so the
host must fall back to `index.html` for unknown paths (Netlify/Vercel do this with
a rewrite rule; on nginx use `try_files $uri /index.html;`).
