# Medical Desert Planner

Track 2 backend for Hack-Nation For India. The project turns the Virtue
Foundation healthcare dataset into evidence-weighted district rankings while
keeping verified medical deserts separate from areas with insufficient data.

## Repository layout

```text
backend/       FastAPI application and Databricks SQL access
frontend/      React, TypeScript and Vite user interface
data_eng/      Spark scoring pipeline and Delta-table materialization
tests/         Backend contract and route tests
api/           Generated OpenAPI specification
docs/          Architecture, deployment and API documentation
app.yaml       Databricks App runtime configuration
requirements.txt
```

The three product areas have independent entry points so backend, frontend and
data-engineering work can be reviewed separately. `data_eng/` intentionally
stays at the repository root because the existing Databricks notebooks import
it as a package. The root `package.json` makes Databricks install and build the
frontend before starting FastAPI.

## Team workflow

GitHub is the source of truth. Create a short-lived branch, pull before editing,
open a pull request, and merge only after backend tests and the frontend build
pass. Databricks deploys the merged `main` branch directly from Git; do not use
workspace file edits or `databricks sync` as the shared development workflow.

## Local development

Authenticate once with the Databricks CLI and use only the workspace host (not
a `/browse/...` URL):

```powershell
.\databricks.exe auth login `
  --host https://dbc-1aa1c463-f7d2.cloud.databricks.com `
  --profile codex
$env:DATABRICKS_CONFIG_PROFILE = "codex"
```

Run the API:

```powershell
python -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

Run the frontend in another terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Vite should call relative `/api` URLs in production. During local development,
configure its proxy to `http://127.0.0.1:8000` when API integration is added.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
Set-Location frontend
npm run lint
npm run build
```

See [the API reference](docs/07-api.md) and the remaining guides in `docs/`.
