# Frontend

React, TypeScript and Vite interface for the Medical Desert Planner.

```text
src/components/  reusable UI and globe components
src/lib/         client utilities and API adapters
src/assets/      bundled visual assets
public/          files copied directly into the production build
```

From this directory:

```powershell
npm install
npm run dev
npm run lint
npm run build
```

The development server proxies relative `/api` requests to FastAPI on port
8000. The production build is written to `dist/`; FastAPI serves that directory
at `/` when it exists. Keep API calls relative so the same code works locally
and in the Databricks App without credentials or CORS configuration in the
browser.
