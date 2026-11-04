# Bulk Email Validator — Frontend

Next.js (App Router, TypeScript) + MUI dashboard for the Bulk Email Validator. See the [repository root README](../README.md) for the full project overview, setup, and development report.

## Local development

```bash
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL if the backend isn't on localhost:8000
npm install
npm run dev
```

## Scripts

- `npm run dev` — start the dev server
- `npm run build` / `npm start` — production build and serve
- `npm run lint` — ESLint
- `npm test` — Jest + React Testing Library
