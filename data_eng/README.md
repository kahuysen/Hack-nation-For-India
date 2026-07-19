# Data engineering

This package owns the batch Spark pipeline. `materialize.py` applies the
teammate scoring modules to all canonical capabilities and writes stable Delta
contracts for the FastAPI application:

- `workspace.default.facility_capability_scores`
- `workspace.default.district_capability_scores`

Run `materialize_notebook.py` as a Databricks notebook job after changing the
scoring rules. API code must consume the output contracts instead of importing
or executing Spark transformations during a request.

Keep imports package-safe (`data_eng.*`) and add capability identifiers through
`contracts.py` so the pipeline and API remain aligned.
