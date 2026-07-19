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

Ontology integration (ontology/*.yaml via ontology_lexicon.py)
--------------------------------------------------------------
When the ontology ships next to this module, corroboration stops being
echo-matching (the same keyword list scanned across every field) and becomes
edge-based: each field is scanned with its OWN vocabulary derived from the
concept graph — a "dialysis" claim is corroborated by "RO water treatment
plant" in `equipment` or "kidney transplant" in `procedure`, evidence a flat
lexicon cannot see. On top of that:
  - word-boundary matching (substring `contains` let "icu" match "curriculum")
  - negated/referral/directory mentions are demoted, with `weak_context_<field>`
    flags so the app can show WHY a field did not count
  - `match_advanced_equipment` flags corroboration by advanced-tier kit
    (cath lab, MRI...) — displayed, never weighted, to stay count-based
If the YAMLs are absent, everything degrades to the hand lexicon below.
"""
from functools import reduce
from operator import add
import re

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

try:
    from .ontology_lexicon import (NEGATION_PATTERN, load_lexicon,
                                   word_boundary_pattern)
except ImportError:  # supports `%run` / direct execution inside a Databricks folder
    try:
        from ontology_lexicon import (NEGATION_PATTERN, load_lexicon,
                                      word_boundary_pattern)
    except ImportError:                                # pragma: no cover
        NEGATION_PATTERN, load_lexicon = None, lambda: None

        def word_boundary_pattern(keywords):
            parts = [re.escape(k.lower()).replace(r"\ ", "[^a-z0-9]+") for k in keywords]
            return "(?i)(?<![a-z0-9])(?:" + "|".join(parts) + ")(?![a-z0-9])"

_ONTOLOGY = load_lexicon()


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


def _has_content(name: str):
    """
    Does a field carry REAL payload (for the corroboration-present count)?

    Many source fields are JSON-encoded arrays stored as strings, so an EMPTY
    field arrives as '[]' — a non-empty string. A bare length check would count
    it as present and inflate n_corrob_present (the content_trust denominator),
    which both fakes "knowledge = 100%" AND deflates content_trust. Strip to
    alphanumerics and reject null-ish placeholders so only real content counts:
      '[]' -> '' (absent) · '["ICU"]' -> 'icu' (present) · 'N/A' -> 'na' (absent)
    """
    alnum = F.regexp_replace(F.lower(_raw(name)), r"[^a-z0-9]", "")
    return (F.length(alnum) > 0) & (~alnum.isin("null", "none", "na", "nan", "nil"))


def _contains_any(text_col, keywords):
    """Boolean column: does text_col contain ANY keyword? (raw substring —
    only safe for the controlled-vocab `specialties` codes)."""
    return reduce(lambda a, b: a | b, [text_col.contains(k) for k in keywords])


def _matches_any(text_col, keywords):
    """Boolean column: word-boundary match of ANY keyword."""
    return text_col.rlike(word_boundary_pattern(keywords))


def _field_keywords(capability: str, base_kws: list) -> dict:
    """
    Per-field keyword sets. With the ontology: field-appropriate vocabularies
    (edge-based corroboration). Without it: the flat lexicon everywhere.
    """
    if _ONTOLOGY is None:
        return {f: base_kws for f in ("capability", "procedure", "equipment", "description")}
    proc = list(dict.fromkeys(_ONTOLOGY.procedure_keywords(capability) + base_kws))
    equip = list(dict.fromkeys(_ONTOLOGY.equipment_keywords(capability) + base_kws))
    union = list(dict.fromkeys(proc + equip))
    return {"capability": union, "procedure": proc, "equipment": equip, "description": union}


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
    kw = word_boundary_pattern(keywords)[4:]        # strip leading (?i), re-add below
    return F.regexp_extract(_raw(name), "(?i)(.{0,50}" + kw + ".{0,50})", 1)


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
                            (free-text fields use word-boundary matching on the
                             ontology's field-specific vocabulary when available)
    weak_context_<field>  : int (0/1)  a hit existed but read as negation/referral/
                            directory-listing, so it was demoted (not counted)
    match_advanced_equipment : int (0/1) equipment corroboration came from
                            advanced-tier kit (ontology tier) — display only
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
    field_kws = _field_keywords(capability, lexicon[capability])

    out = df
    # `specialties` is controlled-vocab codes: hand stems + ontology performed_by ids.
    spec_codes = [c.lower() for c in SPECIALTY_MAP.get(capability, [])]
    if _ONTOLOGY is not None:
        spec_codes = list(dict.fromkeys(spec_codes + _ONTOLOGY.specialty_ids(capability)))

    # --- claim + per-corroborator match & presence ------------------------ #
    # Free-text fields use word-boundary matching on their OWN vocabulary; a hit
    # whose surrounding snippet reads as negation/referral/directory-listing is
    # demoted to 0 and flagged weak_context_<field> (honest uncertainty).
    for f in [CLAIM_FIELD, "procedure", "equipment", "description"]:
        raw_match = _matches_any(_txt(f), field_kws[f])
        snippet = _snippet(f, field_kws[f])
        weak = raw_match & (snippet != "") & snippet.rlike(NEGATION_PATTERN) \
            if NEGATION_PATTERN else F.lit(False)
        out = out.withColumn(f"match_{f}", (raw_match & ~weak).cast("int"))
        out = out.withColumn(f"weak_context_{f}", weak.cast("int"))
    out = out.withColumn("match_specialties",
                         _contains_any(_txt("specialties"), spec_codes).cast("int")
                         if spec_codes else F.lit(0))
    for f in CORROBORATING_FIELDS:
        out = out.withColumn(f"has_{f}", _has_content(f).cast("int"))

    # --- advanced-tier corroboration flag (shown, never weighted) --------- #
    adv_kws = _ONTOLOGY.advanced_equipment_keywords(capability) if _ONTOLOGY else []
    out = out.withColumn(
        "match_advanced_equipment",
        (_matches_any(_txt("equipment"), adv_kws).cast("int") if adv_kws else F.lit(0)))

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
        for f in [CLAIM_FIELD, "procedure", "equipment", "description"]:
            out = out.withColumn(f"snippet_{f}", _snippet(f, field_kws[f]))

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
