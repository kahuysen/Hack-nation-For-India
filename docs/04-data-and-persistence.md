# 4 · Connecting data & persistence

The two integrations our challenge app needs: **reading** the India 10k dataset from a Delta table, and **writing** planner actions (notes, overrides, scenarios) so they survive across sessions.

## Reading a Delta table from the app

Use `databricks-sql-connector` against a serverless SQL warehouse. Pass the warehouse id via `app.yaml`:

```yaml
command: ['streamlit', 'run', 'app.py']
env:
  - name: 'DATABRICKS_WAREHOUSE_ID'
    value: '<warehouse-id>'          # SQL Warehouses → your warehouse → Connection details
  - name: 'FACILITIES_TABLE'
    value: 'workspace.default.india_facilities'
```

```python
import os
import pandas as pd
from databricks import sql

def load_facilities() -> pd.DataFrame:
    with sql.connect(
        server_hostname=os.getenv("DATABRICKS_HOST", "").removeprefix("https://"),
        http_path=f"/sql/1.0/warehouses/{os.environ['DATABRICKS_WAREHOUSE_ID']}",
    ) as conn:
        return pd.read_sql(f"SELECT * FROM {os.environ['FACILITIES_TABLE']}", conn)
```

Inside a deployed app, auth is automatic: the app runs as its **service principal**, and `DATABRICKS_HOST` is provided. Two things to set up once:

1. Grant the service principal `SELECT` on the table (Catalog → table → Permissions).
2. Grant it **Can use** on the SQL warehouse.

Locally, `databricks auth login` credentials are picked up instead.

## Persisting user actions with Lakebase

The challenge requires that notes/overrides/scenarios survive beyond a session, and Lakebase (managed Postgres) is the intended tool — app-local files are wiped on redeploy, so don't rely on them.

1. Create a Lakebase database instance in the workspace UI (**SQL → Lakebase**, available on Free Edition).
2. Add it as an **app resource** (app page → Edit → Resources → add the database) — this grants the service principal access and injects connection env vars (`PGHOST`, `PGDATABASE`, `PGUSER`, …).
3. Connect with any Postgres client (`psycopg` or SQLAlchemy):

```python
import os, psycopg

def save_scenario(capability: str, region: str, note: str) -> None:
    with psycopg.connect(
        host=os.environ["PGHOST"],
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
    ) as conn:
        conn.execute(
            "INSERT INTO scenarios (capability, region, note) VALUES (%s, %s, %s)",
            (capability, region, note),
        )
```

```sql
CREATE TABLE IF NOT EXISTS scenarios (
  id SERIAL PRIMARY KEY,
  capability TEXT NOT NULL,
  region TEXT NOT NULL,
  note TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

## Other stack pieces (where they fit)

| Need | Tool | Notes |
|---|---|---|
| LLM extraction over 10k rows | `ai_query()` in SQL / Agent Bricks | Batch-precompute into a Delta table; never call an LLM in the request path of the app |
| Semantic search over evidence text | Mosaic AI Vector Search | Index the description/evidence columns |
| Tracing the extraction → scoring chain | MLflow 3 Tracing | Stretch goal #1 in the brief |

## Getting the challenge dataset in

The India 10k dataset is shared via the hackathon's Databricks link (see the challenge brief). Once you can see it in Catalog Explorer, either query it directly or `CREATE TABLE workspace.default.india_facilities AS SELECT …` to own a copy you can add computed columns to.
