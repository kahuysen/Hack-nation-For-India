"""
District roll-up — the FINAL function for the Medical Desert map (Track B).

Ties everything together into ONE district-level table the dashboard renders:

  facilities --(trust_scoring + source_trust)--> facility_trust
      |  PIN (address_zipOrPostcode)
      v  india_post_pincode_directory
  district  --aggregate--> trust_weighted_supply, n_records
      |  district name
      v  nfhs_5 (capability_need)
  need_score  --classify--> verdict  (covered / watch / medical_desert / data_desert)

Output contract (one row per district) — what the map consumes:
  state, district, lat, lon,
  n_records            : all facility records in the district (data density)
  n_candidates         : records relevant to the capability
  trust_weighted_supply: sum(facility_trust) over candidates
  need_score           : NFHS need 0..100 (null if capability has no NFHS signal)
  data_confidence      : solid | thin | data_desert   (do we even know this district?)
  verdict              : covered | watch | medical_desert | underserved_need_unknown | data_desert
"""
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from trust_scoring import add_trust_scores, add_facility_trust
from source_trust import add_source_trust
from capability_need import add_need_score

# --- column config (ADJUST to the real india_post_pincode_directory schema) --- #
FAC_PIN = "address_zipOrPostcode"
DIR_PIN, DIR_DIST, DIR_STATE = "pincode", "districtname", "statename"

# --- thresholds (tune with your team) ---------------------------------------- #
SUPPLY_MIN   = 1.0    # trust-weighted supply below this = a gap (≈ <1 fully-trusted facility)
NEED_HI      = 50.0   # NFHS need_score at/above this = high need
MIN_SOLID    = 10     # >= this many records in a district = we can trust the picture
MIN_THIN     = 3      # >= this = thin but usable; below = data desert


def _norm(col):
    """Normalize a district/state name for joining (postal vs NFHS spellings differ)."""
    return F.upper(F.trim(F.regexp_replace(col, r"\s+", " ")))


def attach_district(scored: DataFrame, pincodes: DataFrame) -> DataFrame:
    """Map each facility to a district via its PIN (one district per pincode)."""
    pin_map = (pincodes.select(
                   F.col(DIR_PIN).cast("string").alias("pincode"),
                   F.col(DIR_DIST).alias("district"),
                   F.col(DIR_STATE).alias("state"))
               .dropDuplicates(["pincode"]))
    return (scored
            .withColumn("pincode", F.regexp_extract(F.col(FAC_PIN).cast("string"), r"(\d{6})", 1))
            .join(pin_map, "pincode", "left"))


def aggregate_district(scored_geo: DataFrame) -> DataFrame:
    """Roll facilities up to trust-weighted district supply + a centroid for markers."""
    return (scored_geo.where(F.col("district").isNotNull())
            .groupBy("state", "district")
            .agg(
                F.count("*").alias("n_records"),
                F.sum("is_candidate").alias("n_candidates"),
                F.round(F.sum(F.when(F.col("is_candidate") == 1,
                                     F.col("facility_trust")).otherwise(0.0)), 3)
                 .alias("trust_weighted_supply"),
                F.round(F.avg(F.col("latitude").cast("double")), 5).alias("lat"),
                F.round(F.avg(F.col("longitude").cast("double")), 5).alias("lon"),
            ))


def build_district_table(fac: DataFrame, pincodes: DataFrame, nfhs: DataFrame,
                         capability: str, source_field: str = "websites",
                         combine_mode: str = "product") -> DataFrame:
    """The final function: raw tables + capability -> map-ready district table."""
    # 1. score every facility (content x source trust)
    scored = add_trust_scores(fac, capability)
    scored = add_source_trust(scored, source_field)
    scored = add_facility_trust(scored, mode=combine_mode)

    # 2. facility -> district, then aggregate trust-weighted supply
    supply = aggregate_district(attach_district(scored, pincodes))

    # 3. join NFHS need (normalize district names; postal vs census differ)
    need = (add_need_score(nfhs, capability)
            .select(_norm(F.col("district")).alias("d_key"),
                    F.col("need_score"), F.col("n_indicators")))
    out = (supply.withColumn("d_key", _norm(F.col("district")))
                 .join(need, "d_key", "left").drop("d_key"))

    # 4. data confidence: do we have enough records to conclude anything?
    out = out.withColumn(
        "data_confidence",
        F.when(F.col("n_records") >= MIN_SOLID, "solid")
         .when(F.col("n_records") >= MIN_THIN, "thin")
         .otherwise("data_desert"))

    # 5. verdict — separates a REAL gap from a data gap (the whole point)
    out = out.withColumn(
        "verdict",
        F.when(F.col("data_confidence") == "data_desert", "data_desert")
         .when(F.col("trust_weighted_supply") >= SUPPLY_MIN, "covered")
         # low trust-weighted supply below here:
         .when(F.col("need_score").isNull(), "underserved_need_unknown")
         .when(F.col("need_score") >= NEED_HI, "medical_desert")
         .otherwise("watch"))

    return out.select("state", "district", "lat", "lon",
                      "n_records", "n_candidates", "trust_weighted_supply",
                      "need_score", "data_confidence", "verdict")


def rank_deserts(district_table: DataFrame) -> DataFrame:
    """Highest-risk medical deserts first — feeds the dashboard's ranked list."""
    return (district_table
            .where(F.col("verdict").isin("medical_desert", "underserved_need_unknown"))
            .withColumn("risk_score",
                        F.round(F.coalesce(F.col("need_score"), F.lit(NEED_HI))
                                / (1.0 + F.col("trust_weighted_supply")), 2))
            .orderBy(F.desc("risk_score")))
