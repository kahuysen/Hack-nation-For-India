# Medical Desert Planner 🏥

**Hack-Nation Challenge 04 — Data Legend (Databricks × Virtue Foundation)**

Where are the highest-risk healthcare gaps in India — and how confident are we that they are real?

This Databricks App gives NGO planners **trust-weighted regional coverage** for critical capabilities (ICU, NICU, maternity, emergency, oncology, trauma) built from 10,000 messy facility records. Its core idea: a region can look empty because nothing is there (**medical desert**) or because nobody wrote it down (**data desert**) — and those need different responses.

## How it works

Every facility × capability claim is scored by **cross-field corroboration**: a claimed ICU backed by ventilators in `equipment` and critical-care mentions in `description` counts fully; a bare uncorroborated claim counts a fraction. Regions are then classified on two axes:

| | High knowledge | Low knowledge |
|---|---|---|
| **Low coverage** | 🔴 Medical desert | 🟡 Data desert |
| **High coverage** | 🟢 Served | 🟠 Claimed, unverified |

Every aggregate drills down to the facility records and the exact field mentions ("receipts") behind it. Planner notes and scenarios persist across sessions.

## Repo layout

- `app.py` — Streamlit app (coverage → drill-down → scenarios)
- `trust.py` — claim corroboration + region classification logic
- `app.yaml` — Databricks Apps runtime config
- `data/sample_facilities.csv` — small sample so the app runs without the real dataset

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Runs on the bundled sample data by default.

## Deploy to Databricks Free Edition

1. Install & auth the CLI: `databricks auth login --host https://<your-workspace>.cloud.databricks.com`
2. Create the app once (UI: **New → App**, custom, or CLI):
   ```bash
   databricks apps create medical-desert-planner
   ```
3. Sync this folder and deploy:
   ```bash
   databricks sync . /Workspace/Users/<you>/databricks_apps/medical-desert-planner
   databricks apps deploy medical-desert-planner \
     --source-code-path /Workspace/Users/<you>/databricks_apps/medical-desert-planner
   ```

### Point at the real India 10k dataset

Uncomment and set in `app.yaml` (or the app's environment in the UI):

- `DATABRICKS_WAREHOUSE_ID` — a serverless SQL warehouse id
- `FACILITIES_TABLE` — e.g. `workspace.default.india_facilities`

## Roadmap

- [ ] Load India 10k dataset into a Delta table; map real columns to the app schema
- [ ] Replace keyword corroboration in `trust.py` with LLM evidence extraction (`ai_query`, structured output) + MLflow 3 tracing
- [ ] Replace `scenarios.json` with a Lakebase table
- [ ] Choropleth map of India (PIN-prefix / district level)
- [ ] Best-/worst-case coverage intervals (prediction bands)
