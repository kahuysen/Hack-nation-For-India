# Backend

The FastAPI app is split by responsibility:

```text
app/main.py          application assembly
app/config.py        environment-backed settings
app/database.py      Databricks SQL and CLI OAuth connectivity
app/models.py        public response contracts
app/dependencies.py  request validation shared by routes
app/routes/          operations, planning and evidence endpoints
```

Start it from the repository root with:

```powershell
$env:DATABRICKS_CONFIG_PROFILE = "codex"
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

The API reads only the two materialized tables configured in `app.yaml`; all
expensive Spark scoring stays outside the request path.
