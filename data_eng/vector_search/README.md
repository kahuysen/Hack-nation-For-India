# Local BGE to Databricks AI Search

This package creates a governed semantic-search index without asking
Databricks to compute document embeddings.

```text
prepare_documents -> generate_embeddings -> upload_parquet
    -> materialize_delta -> provision_index -> POST /api/search
```

Generated Parquet files live under `.artifacts/vector_search/` and are ignored
by Git. The uploaded Parquet file is staged in the Unity Catalog volume
`workspace.default.vector_ingest`, then a serverless Spark job writes the
managed, Change-Data-Feed-enabled table
`workspace.default.facility_evidence_embeddings`.

## Local stages

```powershell
$env:DATABRICKS_CONFIG_PROFILE = "codex"
.\.venv\Scripts\python.exe -m data_eng.vector_search.prepare_documents
.\.venv\Scripts\python.exe -m data_eng.vector_search.generate_embeddings
.\.venv\Scripts\python.exe -m data_eng.vector_search.upload_parquet
```

Use `--limit 20` on `prepare_documents` for a quick local smoke test. The BGE
model is downloaded and cached by FastEmbed the first time it runs.

## Databricks stages

Run `materialize_notebook.py` on serverless notebook compute after uploading the
Parquet artifact. Then provision and trigger the Delta Sync index locally:

```powershell
.\.venv\Scripts\python.exe -m data_eng.vector_search.provision_index
```

The source table contract uses `document_id` as a unique primary key and a
384-dimensional `array<float>` column named `embedding`.

## GitHub-first deployment

Commit and push this package before running the Databricks stages. Update the
Databricks Git folder from GitHub, run `materialize_notebook.py` from that Git
folder, and deploy the app from the same folder. The generated Parquet remains
an external build artifact and is uploaded separately to the governed Volume.
