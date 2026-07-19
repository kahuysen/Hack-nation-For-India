"""Load the ontology into Databricks and materialize claim -> concept mapping tables.

Reads specialties.yaml / procedures.yaml / equipment.yaml, loads them into Delta
tables next to the Virtue Foundation dataset, then matches every free-text claim
sentence (procedure, equipment, capability fields) against concept keywords.
The matched keyword doubles as the citation span; claims containing negation or
referral language are kept but flagged match_quality='weak'.

Tables created (catalog.schema = workspace.ontology):
  concepts            one row per ontology concept (vocab, id, label, level, ...)
  keywords            one row per (concept, keyword) — the alias lists
  edges               corroboration graph (performed_by, requires_equipment, ...)
  claim_concepts      one row per (facility, field, claim, concept) match
  facility_specialties exact-tag assignments from the closed specialties field
  facility_concepts   facility x concept rollup for search / aggregation
  facility_claim_counts per-facility claim counts per field (data-desert handling:
                       zero claims means UNKNOWN, not absent)

Run:  uv run --with pyyaml,databricks-sdk python ontology/load_to_databricks.py \
          --profile hacknation --warehouse-id <id>
"""

import argparse
import pathlib
import sys
import time

import yaml
from databricks.sdk import WorkspaceClient

DATASET = "databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities"
SCHEMA = "workspace.ontology"

# Claims that mention a concept while negating, deferring, or merely citing a
# directory listing should not count as strong evidence.
NEGATION_RLIKE = (
    r"(?i)\\b(no|not|without|lacks?|lacking|unavailable|discontinued|closed"
    r"|referred|referral|proposed|planned|upcoming|under construction"
    r"|listed (as|in|among|under)|no longer)\\b"
)


def q(s: str) -> str:
    """SQL string literal."""
    return "'" + s.replace("'", "''") + "'"


class Runner:
    def __init__(self, profile: str, warehouse_id: str):
        self.w = WorkspaceClient(profile=profile)
        self.warehouse_id = warehouse_id

    def sql(self, statement: str):
        r = self.w.statement_execution.execute_statement(
            warehouse_id=self.warehouse_id, statement=statement, wait_timeout="50s"
        )
        while r.status.state.value in ("PENDING", "RUNNING"):
            time.sleep(2)
            r = self.w.statement_execution.get_statement(r.statement_id)
        if r.status.state.value != "SUCCEEDED":
            raise RuntimeError(f"{r.status.state.value}: {r.status.error and r.status.error.message}\n{statement[:500]}")
        return r

    def rows(self, statement: str):
        r = self.sql(statement)
        return r.result.data_array if r.result and r.result.data_array else []


def load_yaml(base: pathlib.Path):
    spec = yaml.safe_load((base / "specialties.yaml").read_text())["specialties"]
    proc = yaml.safe_load((base / "procedures.yaml").read_text())["procedures"]
    equip = yaml.safe_load((base / "equipment.yaml").read_text())["equipment"]
    return spec, proc, equip


def insert_batched(r: Runner, table: str, cols: str, values: list[str], batch=300):
    for i in range(0, len(values), batch):
        r.sql(f"INSERT INTO {table} {cols} VALUES\n" + ",\n".join(values[i : i + batch]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="hacknation")
    ap.add_argument("--warehouse-id", required=True)
    args = ap.parse_args()

    base = pathlib.Path(__file__).parent
    spec, proc, equip = load_yaml(base)
    r = Runner(args.profile, args.warehouse_id)

    r.sql(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    # ── concepts ──────────────────────────────────────────────────
    r.sql(
        f"CREATE OR REPLACE TABLE {SCHEMA}.concepts ("
        "vocab STRING, concept_id STRING, label STRING, category STRING, "
        "level STRING, note STRING)"
    )
    concept_rows = []
    for s in spec:
        concept_rows.append(
            f"('specialty', {q(s['id'])}, {q(s['label'])}, {q(s.get('group',''))}, "
            f"{q(s.get('care_level',''))}, {q(s.get('note',''))})"
        )
    for p in proc:
        concept_rows.append(
            f"('procedure', {q(p['id'])}, {q(p['label'])}, {q(p.get('category',''))}, "
            f"{q(p.get('care_level',''))}, {q(p.get('note',''))})"
        )
    for e in equip:
        concept_rows.append(
            f"('equipment', {q(e['id'])}, {q(e['label'])}, {q(e.get('category',''))}, "
            f"{q(e.get('tier',''))}, {q(e.get('note',''))})"
        )
    insert_batched(r, f"{SCHEMA}.concepts", "(vocab, concept_id, label, category, level, note)", concept_rows)

    # ── keywords (free-text alias lists; procedures + equipment only —
    #    specialty synonyms are display names, too generic for substring matching) ──
    r.sql(f"CREATE OR REPLACE TABLE {SCHEMA}.keywords (vocab STRING, concept_id STRING, keyword STRING)")
    kw_rows = []
    for vocab, entries in (("procedure", proc), ("equipment", equip)):
        for c in entries:
            for k in c.get("keywords", []):
                kw_rows.append(f"({q(vocab)}, {q(c['id'])}, {q(k.lower())})")
    insert_batched(r, f"{SCHEMA}.keywords", "(vocab, concept_id, keyword)", kw_rows)

    # ── edges (corroboration graph) ───────────────────────────────
    r.sql(
        f"CREATE OR REPLACE TABLE {SCHEMA}.edges ("
        "src_vocab STRING, src_id STRING, edge_type STRING, dst_vocab STRING, dst_id STRING)"
    )
    edge_rows = []
    for s in spec:
        for pid in s.get("corroborating_procedures", []):
            edge_rows.append(f"('specialty', {q(s['id'])}, 'corroborating_procedures', 'procedure', {q(pid)})")
        for eid in s.get("corroborating_equipment", []):
            edge_rows.append(f"('specialty', {q(s['id'])}, 'corroborating_equipment', 'equipment', {q(eid)})")
    for p in proc:
        for sid in p.get("performed_by", []):
            edge_rows.append(f"('procedure', {q(p['id'])}, 'performed_by', 'specialty', {q(sid)})")
        for eid in p.get("requires_equipment", []):
            edge_rows.append(f"('procedure', {q(p['id'])}, 'requires_equipment', 'equipment', {q(eid)})")
    for e in equip:
        for pid in e.get("enables", []):
            edge_rows.append(f"('equipment', {q(e['id'])}, 'enables', 'procedure', {q(pid)})")
    insert_batched(r, f"{SCHEMA}.edges", "(src_vocab, src_id, edge_type, dst_vocab, dst_id)", edge_rows)

    print(f"vocab loaded: {len(concept_rows)} concepts, {len(kw_rows)} keywords, {len(edge_rows)} edges")

    # ── claim_concepts: match every free-text claim against every keyword ──
    # Unified concept space: all three free-text fields are matched against the
    # full keyword list, so 'dialysis' evidence is found wherever it lives.
    r.sql(f"""
CREATE OR REPLACE TABLE {SCHEMA}.claim_concepts AS
WITH claims AS (
  SELECT unique_id, 'procedure' AS field, claim
    FROM {DATASET} LATERAL VIEW explode(from_json(`procedure`, 'array<string>')) x AS claim
  UNION ALL
  SELECT unique_id, 'equipment', claim
    FROM {DATASET} LATERAL VIEW explode(from_json(equipment, 'array<string>')) x AS claim
  UNION ALL
  SELECT unique_id, 'capability', claim
    FROM {DATASET} LATERAL VIEW explode(from_json(capability, 'array<string>')) x AS claim
),
-- Word-boundary matching: tokenize both sides (punctuation -> space, padded)
-- so short aliases like 'anc'/'aed' cannot match inside 'balance'/'paediatric'.
clean AS (
  SELECT unique_id, field, claim,
         concat(' ', regexp_replace(lower(claim), '[^a-z0-9]+', ' '), ' ') AS norm
  FROM claims WHERE length(trim(claim)) > 3
)
SELECT
  c.unique_id, c.field, c.claim,
  k.vocab, k.concept_id,
  min(k.keyword) AS matched_alias,
  CASE WHEN c.claim RLIKE '{NEGATION_RLIKE}' THEN 'weak' ELSE 'strong' END AS match_quality
FROM clean c
JOIN {SCHEMA}.keywords k
  ON instr(c.norm, concat(' ', regexp_replace(k.keyword, '[^a-z0-9]+', ' '), ' ')) > 0
GROUP BY c.unique_id, c.field, c.claim, k.vocab, k.concept_id
""")

    # ── facility_specialties: exact tags from the closed vocabulary ──
    r.sql(f"""
CREATE OR REPLACE TABLE {SCHEMA}.facility_specialties AS
SELECT unique_id, specialty AS concept_id, count(*) AS n_mentions
FROM {DATASET} LATERAL VIEW explode(from_json(specialties, 'array<string>')) x AS specialty
GROUP BY unique_id, specialty
""")

    # ── facility_concepts: search/aggregation rollup ──────────────
    r.sql(f"""
CREATE OR REPLACE TABLE {SCHEMA}.facility_concepts AS
SELECT
  m.unique_id, m.vocab, m.concept_id, c.label, c.level,
  sum(CASE WHEN m.match_quality = 'strong' THEN 1 ELSE 0 END) AS n_strong,
  sum(CASE WHEN m.match_quality = 'weak' THEN 1 ELSE 0 END) AS n_weak,
  collect_set(m.field) AS evidence_fields
FROM {SCHEMA}.claim_concepts m
JOIN {SCHEMA}.concepts c ON c.vocab = m.vocab AND c.concept_id = m.concept_id
GROUP BY m.unique_id, m.vocab, m.concept_id, c.label, c.level
""")

    # ── facility_claim_counts: unknown vs absent ──────────────────
    r.sql(f"""
CREATE OR REPLACE TABLE {SCHEMA}.facility_claim_counts AS
SELECT
  unique_id,
  size(from_json(`procedure`, 'array<string>')) AS n_procedure_claims,
  size(from_json(equipment, 'array<string>'))  AS n_equipment_claims,
  size(from_json(capability, 'array<string>')) AS n_capability_claims,
  size(from_json(specialties, 'array<string>')) AS n_specialty_tags
FROM {DATASET}
""")

    # ── coverage report ───────────────────────────────────────────
    print("\n== coverage: claims matched to at least one concept ==")
    for row in r.rows(f"""
WITH claims AS (
  SELECT unique_id, 'procedure' AS field, claim
    FROM {DATASET} LATERAL VIEW explode(from_json(`procedure`, 'array<string>')) x AS claim
  UNION ALL
  SELECT unique_id, 'equipment', claim
    FROM {DATASET} LATERAL VIEW explode(from_json(equipment, 'array<string>')) x AS claim
  UNION ALL
  SELECT unique_id, 'capability', claim
    FROM {DATASET} LATERAL VIEW explode(from_json(capability, 'array<string>')) x AS claim
),
clean AS (SELECT * FROM claims WHERE length(trim(claim)) > 3)
SELECT c.field, count(*) AS claims,
       count(m.claim) AS matched,
       round(100.0 * count(m.claim) / count(*), 1) AS pct
FROM clean c
LEFT JOIN (SELECT DISTINCT unique_id, field, claim FROM {SCHEMA}.claim_concepts) m
  ON m.unique_id = c.unique_id AND m.field = c.field AND m.claim = c.claim
GROUP BY c.field ORDER BY c.field
"""):
        print("  ", row)

    print("\n== top 25 concepts by facility count ==")
    for row in r.rows(f"""
SELECT concept_id, vocab, count(DISTINCT unique_id) AS facilities,
       sum(n_strong) AS strong_claims, sum(n_weak) AS weak_claims
FROM {SCHEMA}.facility_concepts
GROUP BY concept_id, vocab ORDER BY facilities DESC LIMIT 25
"""):
        print("  ", row)

    print("\n== sample of unmatched claims (alias-list gaps) ==")
    for row in r.rows(f"""
WITH claims AS (
  SELECT unique_id, 'procedure' AS field, claim
    FROM {DATASET} LATERAL VIEW explode(from_json(`procedure`, 'array<string>')) x AS claim
  UNION ALL
  SELECT unique_id, 'equipment', claim
    FROM {DATASET} LATERAL VIEW explode(from_json(equipment, 'array<string>')) x AS claim
),
clean AS (SELECT * FROM claims WHERE length(trim(claim)) > 3)
SELECT c.field, c.claim
FROM clean c
LEFT ANTI JOIN {SCHEMA}.claim_concepts m
  ON m.unique_id = c.unique_id AND m.field = c.field AND m.claim = c.claim
ORDER BY rand(42) LIMIT 20
"""):
        print("  ", row)


if __name__ == "__main__":
    sys.exit(main())
