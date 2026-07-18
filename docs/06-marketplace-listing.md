# 6 · The Marketplace listing: what's in the dataset

Notes captured from the **Virtue Foundation Dataset (DAIS 2026)** Databricks Marketplace listing (provider: Databricks, free, installed in our workspace Jul 18 as catalog `databricks_virtue_foundation_dataset_dais_2026`).

## How the data was made

The **Foundational Data Refresh (FDR)** pipeline ingests data from public datasets and websites, applies a medallion architecture, performs GenAI-based information extraction, resolves primary keys across sources, and consolidates disparate records into a single unified row per entity. This is why the brief insists extracted fields are **noisy claims, not ground truth** — they came out of an LLM extraction pipeline (the prompts/Pydantic models are in the challenge starter materials).

## Table 1: `facilities` — the India 10k

Managed Delta table, 15.6 MiB, 51 columns. Full column list (all `string` unless noted):

| Group | Columns |
|---|---|
| Identity & provenance | `unique_id`, `source_types`, `source_ids`, `source_content_id`, `content_table_id`, `cluster_id`, `source`, `source_urls` |
| Basic info | `name`, `organization_type`, `facilityTypeId`, `operatorTypeId`, `affiliationTypeIds`, `yearEstablished`, `acceptsVolunteers`, `description` |
| Contact | `phone_numbers`, `officialPhone`, `email`, `websites`, `officialWebsite`, `facebookLink` |
| Address | `address_line1/2/3`, `address_city`, `address_stateOrRegion`, `address_zipOrPostcode`, `address_country`, `address_countryCode`, `countries` |
| Geo | `coordinates`, `latitude` (double), `longitude` (double) |
| **Claims to verify** | `specialties`, `capability`, `procedure`, `equipment` |
| Size signals | `area`, `numberDoctors`, `capacity` |
| Web-presence signals | `recency_of_page_update`, `distinct_social_media_presence_count`, `affiliated_staff_presence`, `custom_logo_presence`, `number_of_facts_about_the_organization`, `post_metrics_most_recent_social_media_post_date`, `post_metrics_post_count`, `engagement_metrics_n_followers`, `engagement_metrics_n_likes`, `engagement_metrics_n_engagements` |

💡 The web-presence columns are an underused trust signal: a facility with a recently updated page, real staff listings, and active engagement is more credible than one with a stale single-source record — useful input for the trust scorer beyond text corroboration.

## Table 2: `india_post_pincode_directory`

India Post PIN Code Directory from the [Open Government Data Platform India](https://www.data.gov.in/resource/all-india-pincode-directory-till-last-month) (Government Open Data License – India).

- **165,627 rows** — postal geography for all of India: **19,586 unique PIN codes**, 750 districts, 37 states/UTs.
- Columns (11): `circlename`, `regionname`, `divisionname`, `officename`, `pincode`, `officetype`, `delivery`, `district`, `statename`, `latitude`, `longitude`.
- Office types: Branch Office (~140k rows), Post Office (~25k), Head Office (~800).
- ~12,600 rows have `NA` coordinates — not every post office is geocoded.

⚠️ **Row grain is post office, not PIN code.** One PIN can appear on many rows and may map to more than one district or state. A direct join on `pincode` will fan out rows — deduplicate or aggregate first, and check cardinality before joining.

Use for: enriching facility postcodes with district/state, PIN→district lookup tables, understanding postal ambiguity before joins.

## Table 3: `nfhs_5_district_health_indicators`

District fact-sheet data from the [National Family Health Survey 5 (2019–21)](https://www.data.gov.in/catalog/national-family-health-survey-5-nfhs-5-india-districts-factsheet-data-provisional) — the most comprehensive district-level public health dataset for India.

- **706 district rows × 109 indicator columns.**
- Indicator groups: household conditions (electricity, water, sanitation, insurance), maternal/reproductive health (ANC visits, institutional delivery, C-section rate), child health & vaccination, nutrition (stunting, wasting, underweight), anaemia, NCDs (blood sugar/pressure), cancer screening, tobacco, alcohol.

Data quality notes from the listing:

- Column names are long and human-readable — rename to snake_case before loading into Delta.
- District/state names need normalization before joining; spelling and casing vary across datasets.
- `*` values are **suppressed** — treat as NULL, not zero.
- Parenthesized values like `(29.5)` are estimates from 25–49 unweighted cases — use with caution.
- This is NFHS-5 (2019–21); NFHS-6 (2023–24) exists separately with possibly different definitions.

Use for: **demand-side analysis** — comparing facility supply against district health burden, ranking underserved districts where disease burden is high and (trust-weighted) facility coverage is low. This is exactly the enrichment our Medical Desert Planner needs to say "this gap matters most."

## Working with location data (listing guidance)

- To map facilities to districts, prefer a **spatial join**: facility `latitude`/`longitude` against district polygons from [geoBoundaries](https://www.geoboundaries.org) or [DataMeet India Maps](https://datameet.org), via GeoPandas/Shapely, Databricks `ST_Contains`/`ST_Point`, or QGIS.
- **String-matching district names across datasets is unreliable** (spelling/transliteration variance); point-in-polygon on coordinates is more robust wherever coordinates exist.

## General data-quality warning

These are real public-sector datasets: inconsistent place-name casing, ambiguous postal mappings, missing coordinates, suppressed values. The listing's own advice matches the judging criteria: **document how you handle uncertain matches, and don't present inferred geography as exact unless verified.**
