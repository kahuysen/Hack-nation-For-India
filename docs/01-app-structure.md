# 1 · What a Databricks App is made of

A Databricks App is a folder that Databricks runs as a web server on serverless
compute. Our full-stack project separates deployable code from the batch data
pipeline:

```
medical-desert-planner/
├── backend/          # FastAPI application
├── frontend/         # React/Vite source and production build
├── data_eng/         # Spark scoring and Delta materialization
├── tests/            # API and cross-layer contract tests
├── app.yaml          # Databricks runtime command and configuration
└── requirements.txt  # Python dependencies
```

## Backend entry point

`backend/app/main.py` assembles the FastAPI routers and serves `frontend/dist`
when a production frontend build is present. Keeping route, model, database and
configuration modules separate lets backend work proceed without editing a
single shared `app.py`.

Minimal application assembly:

```python
from fastapi import FastAPI

app = FastAPI()
```

## app.yaml

Defines the app entry point and environment:

```yaml
command: ['uvicorn', 'backend.app.main:app', '--host', '0.0.0.0', '--port', '8000']
env:
  - name: 'DATABRICKS_WAREHOUSE_ID'
    value: '<your-sql-warehouse-id>'
```

Notes:

- The command is **not run in a shell**; pass each argument as a YAML list item.
- `env` entries take either a hardcoded `value` or `valueFrom` to reference a secret/resource.
- Databricks supplies the deployed app identity. The backend obtains its OAuth
  credentials through the Databricks SDK and never sends them to React.

## requirements.txt

Standard pip requirements, installed when the app deploys. Pin versions so the deployed app matches what you tested locally:

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
databricks-sql-connector==3.7.0
databricks-sdk>=0.38.0,<1
```

Next: [2 · Create your first app](02-create-first-app.md)
