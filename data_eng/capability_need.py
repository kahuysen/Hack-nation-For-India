"""
Need-side config for the Medical Desert Planner (Track B).

`trust_scoring.py` scores the SUPPLY side (do facilities credibly offer capability X?).
This module scores the NEED side per district, from NFHS-5 district indicators, so the
app can distinguish a real MEDICAL desert (high need + low trusted supply) from a
DATA desert (we simply have too few facility records to say).

Reality of the NFHS-5 data: it is maternal/child-health + NCD focused, so only some
capabilities have a genuine need signal. Each mapping is tagged with its strength.

Two indicator directions:
  - "deficit"  : higher pct = better coverage, so need = 100 - value   (e.g. institutional births)
  - "burden"   : higher pct = more disease,   so need = value          (e.g. hypertension prevalence)

NFHS district key = `district_name`, state key = `state_ut`.
Many pct columns are typed string (footnote markers like '*', '( )'), so coerce defensively.
"""
from functools import reduce

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

NFHS_DISTRICT = "district_name"
NFHS_STATE = "state_ut"

# capability -> list of (nfhs_column, direction). Keys match trust_scoring's lexicon.
# strength noted in comments: *** strong, ** usable, * proxy only.
CAPABILITY_NEED = {
    "maternity": [                                                              # ***
        ("institutional_birth_5y_pct", "deficit"),
        ("births_attended_by_skilled_hp_5y_10_pct", "deficit"),
        ("mothers_who_had_at_least_4_anc_visits_lb5y_pct", "deficit"),          # string col
    ],
    "NICU": [                                                                   # **
        ("institutional_birth_5y_pct", "deficit"),
        ("institutional_birth_in_public_facility_5y_pct", "deficit"),
    ],
    "oncology": [                                                               # **
        ("women_age_30_49_years_ever_undergone_a_cervical_screen_pct", "deficit"),
        ("women_age_30_49_years_ever_undergone_a_breast_exam_pct", "deficit"),
        ("women_age_30_49_years_ever_undergone_an_oral_cancer_exam_pct", "deficit"),
    ],
    "cardiac": [                                                                # ** burden proxy
        ("w15_plus_with_high_bp_sys_gte_140_mmhg_and_or_dia_gte_90_mm_pct", "burden"),
        ("m15_plus_with_high_bp_sys_gte_140_mmhg_and_or_dia_gte_90_mm_pct", "burden"),
    ],
    "ICU": [                                                                    # * proxy: NCD burden
        ("w15_plus_with_high_or_very_high_gt_140_mg_dl_blood_sugar_or_pct", "burden"),
        ("m15_plus_with_high_or_very_high_gt_140_mg_dl_blood_sugar_or_pct", "burden"),
    ],
    "emergency": [                                                              # * weak proxy
        ("births_delivered_by_csection_5y_pct", "deficit"),
    ],
    "trauma": [],   # no NFHS signal — would need road-accident / population data
    "dialysis": [], # no direct NFHS signal
}

# A cross-cutting access modifier: districts with low insurance coverage feel gaps harder.
FINANCIAL_ACCESS_COL = "hh_member_covered_health_insurance_pct"  # deficit


def _num(col_name: str):
    """Coerce a possibly-string NFHS pct column to a double; non-numeric -> null."""
    raw = F.col(col_name).cast("string")
    digits = F.regexp_extract(F.coalesce(raw, F.lit("")), r"(\d+\.?\d*)", 1)
    return F.when(digits == "", F.lit(None).cast("double")).otherwise(digits.cast("double"))


def _need_expr(col_name: str, direction: str):
    """One indicator -> a 0..100 need value (higher = more need)."""
    v = _num(col_name)
    return v if direction == "burden" else (F.lit(100.0) - v)


def has_need_signal(capability: str) -> bool:
    return bool(CAPABILITY_NEED.get(capability))


def add_need_score(nfhs: DataFrame, capability: str) -> DataFrame:
    """
    Return one row per district: district, state, need_score (0..100), n_indicators.
    need_score = mean of available indicator need-values (ignores nulls so sparse
    NFHS rows don't crash to zero). Districts with no usable indicator get need_score = null.
    """
    indicators = CAPABILITY_NEED.get(capability, [])
    base = nfhs.select(
        F.col(NFHS_DISTRICT).alias("district"),
        F.col(NFHS_STATE).alias("state"),
        *[_need_expr(c, d).alias(f"need_{i}") for i, (c, d) in enumerate(indicators)],
    )
    if not indicators:
        # no signal for this capability -> explicit null, so the app can say "need unknown"
        return base.withColumn("need_score", F.lit(None).cast("double")) \
                   .withColumn("n_indicators", F.lit(0))

    need_cols = [F.col(f"need_{i}") for i in range(len(indicators))]
    n_present = reduce(lambda a, b: a + b, [c.isNotNull().cast("int") for c in need_cols])
    # nan-safe mean: sum of non-nulls / count of non-nulls
    total = reduce(lambda a, b: a + b, [F.coalesce(c, F.lit(0.0)) for c in need_cols])
    mean_need = F.when(n_present > 0, F.round(total / n_present, 2)).otherwise(F.lit(None).cast("double"))
    return base.withColumn("need_score", mean_need).withColumn("n_indicators", n_present)
