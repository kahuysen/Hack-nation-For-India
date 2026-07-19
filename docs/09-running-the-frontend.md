# 9 · Running the Frontend

The frontend is a **Vite + React + TypeScript** app that renders the Medical
Desert Planner globe (`react-globe.gl`). It currently runs on **dummy data** — no
backend or Databricks connection is required to develop or view it.

## Prerequisites

- **Node.js 20+** (Vite 8 requires it; the repo is developed on Node 24).
- npm (bundled with Node).

## Install & run

```bash
cd frontend
npm install
npm run dev
```

Vite prints the local URL — **http://localhost:5173/** (it auto-picks the next
free port, e.g. `5174`, if 5173 is taken). Open it in a browser.

You should see a 3D globe centered on India with states shaded by medical-desert
**status** (🔴 medical desert / 🟠 claimed-unverified / 🟡 data desert /
🟢 served), a capability dropdown in the header, and a status legend. Hover a
state for its (dummy) evidence tooltip.

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Start the dev server with hot-reload |
| `npm run build` | Type-check (`tsc -b`) and build to `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | Run oxlint |

## Where the dummy data lives

- `src/lib/dummyRegions.ts` — per-state status + trust-weighted metrics, shaped to
  mirror the real `GET /api/regions` response. Swapping to live data later means
  replacing this source (see the design spec).
- `public/india-states.geojson` — simplified India state boundaries (~61 KB, 34
  states) used for the choropleth. `public/countries.geojson` is the world base
  layer.

## API integration

The app already speaks the real API contract (`src/lib/api.ts`, matching
`api/openapi.json` v2.0.0): `/api/capabilities`, `/api/regions` (verdict-based
`RegionResult`), `/api/facilities` (`FacilityEvidence` with row-level evidence).

`src/lib/dataSource.ts` chooses the source by env flag:

| Env | Effect |
|---|---|
| _(unset)_ | **Dummy data** shaped to the real contract (default; local dev) |
| `VITE_USE_API=true` | Call the **live API** |
| `VITE_API_BASE=<url>` | Override the API origin (default: same-origin) |

The deployed API is behind Databricks SSO, so `VITE_USE_API=true` only works
**same-origin inside the Databricks App** (SSO cookie) — not from a local browser.
For local dev, keep the dummy source. See
`docs/superpowers/specs/2026-07-19-india-healthcare-globe-design.md` for the full
plan (region model, persistence).

> Note: the live `/api/regions` is **district-grain**; the current choropleth is
> **state-grain** (vendored state GeoJSON). Going live means either a district
> GeoJSON or rolling districts up to states for the map.

## Taking a screenshot (optional)

With the dev server running, a small Playwright probe captures the globe:

```bash
node probe-desert.mjs   # writes probe-desert.png (gitignored)
```

Adjust the port in the script if the dev server isn't on 5174.
