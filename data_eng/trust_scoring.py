"""
Trust scoring for the Medical Desert Planner (Track B).

Core idea (matches the challenge rubric): a facility's CLAIM to a capability is
trusted in proportion to how many INDEPENDENT fields corroborate it. A bare
capability claim with no supporting text scores low ("weak"); a claim echoed by
procedure + equipment + description scores high ("strong").

Everything here is transparent and tunable so the app can show its receipts:
- per-field match flags          -> which fields agreed
- snippet_<field>                -> the exact text that matched (citations)
- content_trust in [0, 1]        -> n_corroborating / n_corrob_present (weight-free)
- trust_band                     -> strong / moderate / weak / none
- data_confidence                -> high / medium / low (for data-desert vs medical-desert)
- unsupported_claim              -> claim present but ZERO corroboration (review-queue flag)
- add_facility_trust(...)        -> combine content_trust with source_trust

Works on the raw `facilities` table where all evidence fields are strings.
Import this from both the EDA notebook and the Databricks App.
"""
from functools import reduce
from operator import add
import re

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


# --------------------------------------------------------------------------- #
# 1. Capability lexicon — the planner's dropdown maps to these keyword sets.
#    Keywords are matched case-insensitively as substrings, so JSON-list-encoded
#    string fields (e.g. '["Level II trauma center","ICU"]') still match.
# --------------------------------------------------------------------------- #
CAPABILITY_LEXICON = {
    "ICU":       ["icu", "intensive care", "critical care unit", "critical care"],
    "NICU":      ["nicu", "neonatal intensive", "neonatal icu", "neonatology"],
    "maternity": ["maternity", "obstetric", "labour room", "labor room", "delivery room",
                  "cesarean", "caesarean", "c-section", "gynaec", "gynecolog", "antenatal"],
    "emergency": ["emergency", "casualty", "24x7", "24/7", "ambulance", "trauma"],
    "oncology":  ["oncology", "cancer", "chemotherapy", "radiotherapy", "tumour", "tumor", "oncologist"],
    "trauma":    ["trauma", "emergency surgery", "orthopaedic surgery", "orthopedic surgery", "icu"],
    "dialysis":  ["dialysis", "haemodialysis", "hemodialysis", "nephrology"],
    "cardiac":   ["cardiac", "cardiology", "cath lab", "angioplasty", "coronary care", "ccu"],
}

# The claim field vs. the independent corroborating fields.
# content_trust is COUNT-BASED (no arbitrary weights, symmetric with source_trust):
#   content_trust = (# corroborating fields that mention X) / (# corroborating fields present)
# The claim field (`capability`) gates candidacy; the others corroborate.
CLAIM_FIELD = "capability"
CORROBORATING_FIELDS = ["procedure", "equipment", "description", "specialties"]

# `specialties` is a CONTROLLED VOCABULARY (camelCase codes), NOT free text. Match
# lowercased STEMS as substrings against the codes, so we catch both level-1 codes
# and subspecialties (e.g. "oncolog" -> medicalOncology / surgicalOncology /
# pediatricHematologyOncology). Canonical mappings per medical_specialties.py:
# trauma -> criticalCareMedicine, emergency -> emergencyMedicine.
SPECIALTY_MAP = {
    "ICU":       ["criticalcare"],
    "NICU":      ["neonatolog"],
    "maternity": ["obstetric", "gynecolog"],
    "emergency": ["emergency"],
    "oncology":  ["oncolog"],
    "trauma":    ["trauma", "criticalcare"],
    "dialysis":  ["nephrolog"],
    "cardiac":   ["cardiolog", "cardiacsurgery"],
}


def available_capabilities():
    """Keys the app dropdown can offer."""
    return sorted(CAPABILITY_LEXICON.keys())


# --------------------------------------------------------------------------- #
# small column helpers
# --------------------------------------------------------------------------- #
def _txt(name: str):
    """Lowercased, null-safe string column (for matching)."""
    return F.lower(F.coalesce(F.col(name).cast("string"), F.lit("")))


def _raw(name: str):
    """Original-case, null-safe string column (for readable snippets)."""
    return F.coalesce(F.col(name).cast("string"), F.lit(""))


def _contains_any(text_col, keywords):
    """Boolean column: does text_col contain ANY keyword?"""
    return reduce(lambda a, b: a | b, [text_col.contains(k) for k in keywords])


def _int_or_zero(name: str, max_reasonable: int = 10000):
    """
    Pull the first integer out of a messy string column; 0 if none/garbage.

    Cast to LONG (not int) so big junk values don't overflow int32 under ANSI mode,
    then discard anything outside [0, max_reasonable] — the raw `capacity` /
    `numberDoctors` fields contain garbage like '189190037606664', which is not a
    real bed count and must not count as structured backing.
    """
    d = F.regexp_extract(_raw(name), r"(\d+)", 1)
    n = F.when(d == "", F.lit(None)).otherwise(d.cast("long"))
    n = F.when((n >= 0) & (n <= max_reasonable), n).otherwise(F.lit(None))
    return F.coalesce(n, F.lit(0))


def _snippet(name: str, keywords):
    """Extract ~50 chars of context around the first keyword hit (a citation)."""
    pattern = "(?i)(.{0,50}(?:" + "|".join(re.escape(k) for k in keywords) + ").{0,50})"
    return F.regexp_extract(_raw(name), pattern, 1)


# --------------------------------------------------------------------------- #
# 2. The scoring function
# --------------------------------------------------------------------------- #
def add_trust_scores(df: DataFrame, capability: str,
                     lexicon: dict = None, with_snippets: bool = True) -> DataFrame:
    """
    Add COUNT-BASED trust-scoring columns to `df` for a single `capability`.
    No weights: content_trust = corroborating fields / corroborating fields present.

    Added columns
    -------------
    match_capability      : int (0/1)  the claim field mentions the capability
    match_<field>         : int (0/1)  per corroborating field (procedure/equipment/description/specialties)
    n_corroborating       : int   corroborating fields that mention it (0-4)
    n_corrob_present      : int   corroborating fields that have any text (0-4)  -> confidence
    content_trust         : double [0,1] = n_corroborating / n_corrob_present
    is_candidate          : int   claims it OR any field evidences it
    unsupported_claim     : int   claimed but zero corroboration
    trust_band            : strong (>=2) | moderate (1) | weak (claim,0) | none
    data_confidence       : high (>=3 present) | medium (>=1) | low
    snippet_*             : string exact matching text (only if with_snippets)
    """
    lexicon = lexicon or CAPABILITY_LEXICON
    if capability not in lexicon:
        raise ValueError(f"Unknown capability '{capability}'. "
                         f"Choose from {sorted(lexicon)}")
    kws = lexicon[capability]

    out = df
    spec_codes = [c.lower() for c in SPECIALTY_MAP.get(capability, [])]

    # --- claim + per-corroborator match & presence ------------------------ #
    # `specialties` matches on controlled-vocab CODES; other fields use free-text keywords.
    out = out.withColumn("match_capability", _contains_any(_txt(CLAIM_FIELD), kws).cast("int"))
    for f in CORROBORATING_FIELDS:
        terms = spec_codes if f == "specialties" else kws
        match_expr = _contains_any(_txt(f), terms).cast("int") if terms else F.lit(0)
        out = out.withColumn(f"match_{f}", match_expr)
        out = out.withColumn(f"has_{f}", (F.length(F.trim(_raw(f))) > 0).cast("int"))

    # --- counts: how many corroborators agree, of those present ----------- #
    out = out.withColumn("n_corroborating",
                         reduce(add, [F.col(f"match_{f}") for f in CORROBORATING_FIELDS]))
    out = out.withColumn("n_corrob_present",
                         reduce(add, [F.col(f"has_{f}") for f in CORROBORATING_FIELDS]))

    # --- content_trust = fraction of PRESENT corroborators that agree ----- #
    out = out.withColumn(
        "content_trust",
        F.when(F.col("n_corrob_present") > 0,
               F.round(F.col("n_corroborating") / F.col("n_corrob_present"), 3))
         .otherwise(F.lit(0.0)),
    )

    out = out.withColumn(
        "is_candidate",
        ((F.col("match_capability") == 1) | (F.col("n_corroborating") > 0)).cast("int"))
    out = out.withColumn(
        "unsupported_claim",
        ((F.col("match_capability") == 1) & (F.col("n_corroborating") == 0)).cast("int"))

    # --- band from the corroboration COUNT (weight-free) ------------------ #
    out = out.withColumn(
        "trust_band",
        F.when(F.col("is_candidate") == 0, "none")
         .when(F.col("n_corroborating") >= 2, "strong")
         .when(F.col("n_corroborating") == 1, "moderate")
         .otherwise("weak"),                          # claimed but nothing corroborates
    )

    # --- data confidence: separate from trust (data-desert signal) -------- #
    out = out.withColumn(
        "data_confidence",
        F.when(F.col("n_corrob_present") >= 3, "high")
         .when(F.col("n_corrob_present") >= 1, "medium")
         .otherwise("low"),
    )

    # --- citations: the exact snippet each field matched ------------------ #
    if with_snippets:
        out = out.withColumn("snippet_capability", _snippet(CLAIM_FIELD, kws))
        for f in ["procedure", "equipment", "description"]:
            out = out.withColumn(f"snippet_{f}", _snippet(f, kws))

    return out


# --------------------------------------------------------------------------- #
# 3. Combine content trust (this module) with source trust into facility_trust
# --------------------------------------------------------------------------- #
def add_facility_trust(scored: DataFrame, mode: str = "product") -> DataFrame:
    """
    Combine `content_trust` (claim corroboration) with `source_trust` (provenance)
    into one `facility_trust`. Run add_trust_scores AND add_source_trust first.
      mode="product" : content_trust * source_trust  (strict AND — both must hold)
      mode="mean"    : average of the two            (lenient)
      mode="min"     : the weaker of the two         (most conservative)
    """
    c, s = F.col("content_trust"), F.col("source_trust")
    combined = {"product": c * s, "mean": (c + s) / 2, "min": F.least(c, s)}[mode]
    return scored.withColumn("facility_trust", F.round(combined, 3))


# --------------------------------------------------------------------------- #
# 4. Quick eyeball helper (use in the notebook, not the app)
# --------------------------------------------------------------------------- #
def band_summary(scored: DataFrame):
    """Count candidate facilities per trust_band."""
    return (scored.where(F.col("is_candidate") == 1)
                  .groupBy("trust_band")
                  .count()
                  .orderBy(F.desc("count")))
