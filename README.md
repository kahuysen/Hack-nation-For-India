# Hack-Nation For India 🏥

**Challenge 04 — Data Legend (Databricks × Virtue Foundation)**
Building the trust layer for Indian healthcare: turning 10,000 messy facility records into decisions NGO planners can defend.

Our track: **Medical Desert Planner** — where are the highest-risk gaps, and how confident are we that they're real? The core idea is separating **medical deserts** (verified gaps) from **data deserts** (we simply don't know), by scoring every capability claim against corroborating evidence across fields.

## Docs: how to build a Databricks App

Step-by-step guides for getting our app onto Databricks Free Edition:

1. [App structure](docs/01-app-structure.md) — the three files every app needs (`app.py`, `app.yaml`, `requirements.txt`) with examples
2. [Create your first app](docs/02-create-first-app.md) — Free Edition signup, UI templates, CLI creation
3. [Develop & deploy](docs/03-develop-and-deploy.md) — the local dev loop, `databricks sync` + `deploy`, deploying from GitHub, debugging
4. [Data & persistence](docs/04-data-and-persistence.md) — reading Delta tables from the app, Lakebase for planner notes/scenarios, where Vector Search and MLflow fit
5. [Loading the dataset](docs/05-loading-the-dataset.md) — installing the Virtue Foundation Marketplace listing, making a writable copy, granting app access, sanity checks
6. [Marketplace listing notes](docs/06-marketplace-listing.md) — the three tables (facilities 51-col schema, PIN code directory, NFHS-5 health indicators), join caveats, geo guidance
7. [API reference](docs/07-api.md) — the deployed app's FastAPI endpoints (regions ranking, facility evidence), auth, examples; spec snapshot in [api/openapi.json](api/openapi.json)

## Quick reference

```bash
# one-time
databricks auth login --host https://<workspace>.cloud.databricks.com
databricks apps create medical-desert-planner

# every iteration
databricks sync . /Workspace/Users/<you>/databricks_apps/medical-desert-planner
databricks apps deploy medical-desert-planner \
  --source-code-path /Workspace/Users/<you>/databricks_apps/medical-desert-planner
```
