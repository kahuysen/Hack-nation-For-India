# 5 · Loading the dataset into Databricks

The challenge dataset is distributed through **Databricks Marketplace** as a free listing: *Virtue Foundation Dataset (DAIS 2026)*. You don't upload anything — installing the listing mounts a shared catalog in your workspace.

## Install from Marketplace

1. Open the listing link from the challenge brief (or search Marketplace for "Virtue Foundation"). Log into your **Free Edition** workspace when prompted.
2. Click **Get instant access** — the listing is free and Databricks-provided.
3. A new catalog appears under **Catalog → Shares received**:

```
databricks_virtue_foundation_dataset_dais_2026
└── virtue_foundation_dataset
    ├── facilities                          # the India 10k (51 columns)
    ├── india_post_pincode_directory        # 165k rows of postal geography
    └── nfhs_5_district_health_indicators   # 706 districts × 109 health indicators
```

> ✅ Already done in our workspace (installed Jul 18). Fully-qualified table name:
> `databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities`

Verify with:

```sql
SELECT count(*) FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities;
```

## Make a writable working copy

The shared catalog is **read-only** — you can't add computed columns (trust scores, extracted evidence) to it. Create your own copy in the `workspace` catalog, fixing types as you go (almost every column arrives as `string`, including numeric ones):

```sql
CREATE TABLE workspace.default.facilities AS
SELECT
  unique_id,
  name,
  facilityTypeId,
  operatorTypeId,
  address_city,
  address_stateOrRegion,
  address_zipOrPostcode,
  latitude,                                  -- already double
  longitude,                                 -- already double
  description,
  specialties,
  capability,                                -- claim, not fact
  procedure,                                 -- claim, not fact
  equipment,                                 -- claim, not fact
  TRY_CAST(numberDoctors AS INT)   AS numberDoctors,
  TRY_CAST(capacity AS INT)        AS capacity,
  TRY_CAST(yearEstablished AS INT) AS yearEstablished,
  source_urls
FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities;
```

Use `TRY_CAST` (not `CAST`) — messy values become `NULL` instead of failing the whole statement. Add the remaining columns as needed; the full 51-column list is in [guide 6](06-marketplace-listing.md).

Copy the two supplemental tables the same way if you use them.

## Grant access to the app

The Databricks App runs as its own **service principal**, which sees nothing by default:

1. Catalog Explorer → your table → **Permissions** → grant `SELECT` to the app's service principal.
2. SQL Warehouses → your warehouse → **Permissions** → grant **Can use**.

Then point the app at the table via `app.yaml` env vars (see [guide 4](04-data-and-persistence.md)):

```yaml
env:
  - name: 'FACILITIES_TABLE'
    value: 'workspace.default.facilities'
```

## First sanity checks

```sql
-- field coverage (should roughly match the brief: capability 99.7%, equipment 77%, capacity 25%…)
SELECT
  round(avg(CASE WHEN description IS NOT NULL AND description != '' THEN 1 ELSE 0 END) * 100, 1) AS pct_description,
  round(avg(CASE WHEN capability  IS NOT NULL AND capability  != '' THEN 1 ELSE 0 END) * 100, 1) AS pct_capability,
  round(avg(CASE WHEN equipment   IS NOT NULL AND equipment   != '' THEN 1 ELSE 0 END) * 100, 1) AS pct_equipment,
  round(avg(CASE WHEN capacity    IS NOT NULL THEN 1 ELSE 0 END) * 100, 1)                       AS pct_capacity
FROM workspace.default.facilities;

-- how clean is the geography?
SELECT address_stateOrRegion, count(*) FROM workspace.default.facilities
GROUP BY 1 ORDER BY 2 DESC LIMIT 40;
```

Expect casing/spelling variants in state and district names — normalize before any regional rollup, or use `latitude`/`longitude` with a spatial join instead (see guide 6's "Working with location data").
