# 7 · Medical Desert Planner API

The deployed Databricks App exposes a FastAPI backend. Spec snapshot: [api/openapi.json](../api/openapi.json) (v1.0.0).

- **Base URL:** `https://hacknation-for-india-7474650499580242.aws.databricksapps.com`
- **Interactive docs:** [`/docs`](https://hacknation-for-india-7474650499580242.aws.databricksapps.com/docs) (Swagger UI), spec at `/openapi.json`
- **What it does:** combines trust-weighted capability evidence from 10,088 facilities with NFHS-5 district health indicators, and reports uncertainty honestly.

## Authentication

The app URL sits behind Databricks workspace auth. In a browser you're redirected through SSO. For `curl`/scripts, send an OAuth token for the workspace:

```bash
TOKEN=$(databricks auth token --host https://dbc-99fcde8c-87d9.cloud.databricks.com | jq -r .access_token)
curl -H "Authorization: Bearer $TOKEN" \
  "https://hacknation-for-india-7474650499580242.aws.databricksapps.com/api/health"
```

## Endpoints

### `GET /api/health` — Operations

Backend readiness probe. Returns 200 when the app is up.

### `GET /api/capabilities` — Planning

Lists the capability values accepted by the scoring endpoints.

```json
{ "capabilities": ["ICU", "NICU", "Emergency care", "Maternity", "Oncology", "Trauma center"] }
```

### `GET /api/regions` — Planning

Ranks geographies by health need, care gap, and confidence in the evidence.

| Param | Type | Required | Default | Notes |
|---|---|---|---|---|
| `capability` | string | ✅ | — | e.g. `NICU` (use `/api/capabilities` values) |
| `level` | `state` \| `district` | — | `district` | rollup grain |
| `limit` | int 1–706 | — | 50 | max = number of NFHS-5 districts |

Returns `RegionResult[]`:

| Field | Type | Meaning |
|---|---|---|
| `region` | string | state or district name |
| `facilities` | int | records in the region |
| `claiming` | int | facilities claiming the capability |
| `corroborated` | int | claims backed by cross-field evidence |
| `coverage` | 0–1 | trust-weighted supply |
| `knowledge` | 0–1 | how much we actually know (completeness) |
| `health_need` | 0–1 \| null | NFHS-5 district health burden (null = no match) |
| `priority_score` | 0–1 | need × gap × confidence ranking signal |
| `status` | string | 🔴 medical desert / 🟡 data desert / 🟠 claimed-unverified / 🟢 served |

Example:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/regions?capability=NICU&level=district&limit=20"
```

### `GET /api/facilities` — Evidence

The facility-level evidence behind a regional score — the "receipts" drill-down.

| Param | Type | Required | Default |
|---|---|---|---|
| `capability` | string | ✅ | — |
| `state` | string | — | — |
| `district` | string | — | — |
| `limit` | int 1–500 | — | 100 |

Returns `FacilityEvidence[]`:

| Field | Type | Meaning |
|---|---|---|
| `facility_id`, `name`, `state`, `district`, `pin` | | identity & location |
| `tier` | string | Corroborated / Claimed only / … |
| `trust_weight` | number | contribution to regional coverage |
| `knowledge` | number | record completeness |
| `evidence` | `[source_field, matching_text][]` | row-level citations |
| `description` | string \| null | facility free text |
| `latitude`, `longitude` | number \| null | for mapping |
| `source_urls` | string \| null | provenance links |

Example:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/facilities?capability=Emergency%20care&state=Bihar&limit=50"
```

Errors: invalid params return FastAPI's standard `422` validation payload.

## Keeping the spec in sync

After changing the backend, refresh the snapshot:

```bash
curl -H "Authorization: Bearer $TOKEN" "$BASE/openapi.json" | jq . > api/openapi.json
```
