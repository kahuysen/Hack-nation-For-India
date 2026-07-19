# Medical Desert Planner API v2

The FastAPI service reads the two tables produced by `data_eng.materialize`.
It does not score raw records during HTTP requests.

- Interactive docs: `/docs`
- ReDoc: `/redoc`
- OpenAPI: `/openapi.json`
- Base API path: `/api`

## Data contract

Run `data_eng/materialize_notebook.py` before deploying or after changing the
source dataset. It overwrites:

```text
workspace.default.facility_capability_scores
workspace.default.district_capability_scores
```

## `GET /api/health`

Checks that both materialized tables can be queried and returns their row counts.
It returns HTTP `503` when the pipeline outputs are unavailable.

## `GET /api/capabilities`

Returns stable machine IDs, display labels, and whether NFHS-5 supplies a need
signal. API requests should use the machine ID.

```json
{
  "capabilities": [
    {"id": "nicu", "label": "NICU", "has_need_signal": true},
    {"id": "trauma", "label": "Trauma center", "has_need_signal": false}
  ]
}
```

## `GET /api/regions`

Ranks districts using the batch pipeline's `risk_score`.

| Parameter | Required | Notes |
|---|---:|---|
| `capability` | yes | Stable ID from `/api/capabilities` |
| `state` | no | Case-insensitive exact filter |
| `verdict` | no | `covered`, `watch`, `medical_desert`, `underserved_need_unknown`, or `data_desert` |
| `limit` | no | 1-706; default 50 |

Important response measures:

- `trust_weighted_supply`: sum of candidate facility trust scores.
- `coverage`: mean facility trust among candidates, from 0 to 1.
- `knowledge`: mean corroborating-field completeness, from 0 to 1.
- `need_score`: capability-specific NFHS-5 need, from 0 to 100, or null.
- `risk_score`: normalized need x care gap x evidence completeness.
- `data_confidence` and `verdict`: explicit distinction between medical and data deserts.

```bash
curl "$BASE/api/regions?capability=nicu&verdict=medical_desert&limit=20"
```

## `GET /api/facilities`

Returns the precomputed facility evidence behind district classifications.

| Parameter | Required | Notes |
|---|---:|---|
| `capability` | yes | Stable capability ID |
| `state` | no | Case-insensitive exact filter |
| `district` | no | Case-insensitive exact filter |
| `candidates_only` | no | Default `true` |
| `limit` | no | 1-500; default 100 |

Each result includes `tier`, `trust_weight`, `source_trust`, `knowledge`, exact
evidence snippets, coordinates, and source URLs.

```bash
curl "$BASE/api/facilities?capability=emergency&district=Patna&limit=50"
```

## `POST /api/search`

Runs semantic similarity search over the governed Databricks AI Search index.
Document embeddings are generated locally with `BAAI/bge-small-en-v1.5`, stored
in a Unity Catalog managed Delta table, and synchronized to AI Search. Query
embeddings use the same model and dimension.

```json
{
  "query": "hospital with neonatal intensive care",
  "state": "Bihar",
  "district": "Patna",
  "limit": 10
}
```

`state` and `district` are optional exact-match filters. `limit` accepts 1-50
and defaults to 10. Results include facility identity, geography, coordinates,
source URLs, the indexed evidence text, and a similarity score.

The endpoint returns HTTP `503` while the AI Search index is unavailable or
still synchronizing.

## Refreshing the checked-in specification

```powershell
.\.venv\Scripts\python.exe -c `
  "import json; from backend.app.main import app; print(json.dumps(app.openapi(), indent=2))" `
  | Set-Content api/openapi.json
```
