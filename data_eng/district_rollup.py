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

try:
    from .trust_scoring import add_trust_scores, add_facility_trust
    from .source_trust import add_source_trust
    from .capability_need import add_need_score
except ImportError:  # supports `%run` / direct execution inside a Databricks folder
    from trust_scoring import add_trust_scores, add_facility_trust
    from source_trust import add_source_trust
    from capability_need import add_need_score

# --- column config (ADJUST to the real india_post_pincode_directory schema) --- #
FAC_PIN = "address_zipOrPostcode"
DIR_PIN, DIR_DIST, DIR_STATE = "pincode", "district", "statename"

# --- thresholds (tune with your team) ---------------------------------------- #
COVERAGE_OK  = 0.30   # mean facility_trust (0-1) at/above this = relatively covered.
                      # Uses the SAME normalized signal as risk_score's (1-coverage),
                      # not the raw unbounded trust_weighted_supply sum.
NEED_HI      = 50.0   # NFHS need_score at/above this = high need
MIN_SOLID    = 10     # >= this many records in a district = we can trust the picture
MIN_THIN     = 3      # >= this = thin but usable; below = data desert


def _norm(col):
    """Normalize a district/state name for joining (postal vs NFHS spellings differ)."""
    normalized = F.upper(F.coalesce(col.cast("string"), F.lit("")))
    normalized = F.regexp_replace(normalized, "&", " AND ")
    normalized = F.regexp_replace(normalized, r"[^A-Z0-9 ]", " ")
    return F.trim(F.regexp_replace(normalized, r"\s+", " "))


def _norm_state(col):
    """Normalize common postal/NFHS state aliases before joining."""
    normalized = _norm(col)
    return (F.when(normalized.isin("NCT OF DELHI", "NCT DELHI"), "DELHI")
             .when(normalized == "ORISSA", "ODISHA")
             .when(normalized == "PONDICHERRY", "PUDUCHERRY")
             .when(normalized == "UTTARANCHAL", "UTTARAKHAND")
             .otherwise(normalized))


def attach_district(scored: DataFrame, pincodes: DataFrame) -> DataFrame:
    """Map each facility to a district via its PIN (one district per pincode)."""
    pin_map = (pincodes.select(
                   F.col(DIR_PIN).cast("string").alias("pincode"),
                   F.col(DIR_DIST).alias("district"),
                   F.col(DIR_STATE).alias("state"))
               .dropDuplicates(["pincode"]))
    return (scored
            .withColumn("pincode", F.regexp_extract(F.col(FAC_PIN).cast("string"), r"(\d{6})", 1))
            .join(pin_map, "pincode", "left")
            .withColumn("state", F.coalesce("state", "address_stateOrRegion"))
            .withColumn("district", F.coalesce("district", "address_city", "area")))


def build_facility_table(fac: DataFrame, pincodes: DataFrame, capability: str,
                         source_field: str = "source_urls",
                         combine_mode: str = "product") -> DataFrame:
    """Create the facility-level evidence table consumed by the drill-down API."""
    scored = add_trust_scores(fac, capability)
    scored = add_source_trust(scored, source_field)
    scored = add_facility_trust(scored, mode=combine_mode)
    return attach_district(scored, pincodes).withColumn("capability_id", F.lit(capability))


def aggregate_district(scored_geo: DataFrame) -> DataFrame:
    """Roll facilities up to trust-weighted district supply + a centroid for markers."""
    return (scored_geo.where(F.col("district").isNotNull())
            .groupBy("state", "district")
            .agg(
                 F.count("*").alias("n_records"),
                 F.sum("is_candidate").alias("n_candidates"),
                 F.sum("match_capability").alias("claiming"),
                 F.sum(F.when(F.col("n_corroborating") > 0, 1).otherwise(0)).alias("corroborated"),
                 F.round(F.sum(F.when(F.col("is_candidate") == 1,
                                      F.col("facility_trust")).otherwise(0.0)), 3)
                  .alias("trust_weighted_supply"),
                 F.round(F.avg(F.when(F.col("is_candidate") == 1,
                                      F.col("facility_trust"))), 3).alias("coverage"),
                 F.round(F.avg(F.col("n_corrob_present") / F.lit(4.0)), 3).alias("knowledge"),
                 F.round(F.avg("source_trust"), 3).alias("mean_source_trust"),
                 F.round(F.avg(F.when(
                     F.col("latitude").cast("double").between(6.0, 37.5)
                     & F.col("longitude").cast("double").between(68.0, 98.5),
                     F.col("latitude").cast("double"))), 5).alias("lat"),
                 F.round(F.avg(F.when(
                     F.col("latitude").cast("double").between(6.0, 37.5)
                     & F.col("longitude").cast("double").between(68.0, 98.5),
                     F.col("longitude").cast("double"))), 5).alias("lon"),
             ))


def build_district_from_scored(scored_geo: DataFrame, nfhs: DataFrame,
                               capability: str) -> DataFrame:
    """Aggregate a scored facility frame and attach the complete NFHS district universe."""
    supply = aggregate_district(scored_geo)

    # Join on both normalized state and district. Starting from a full join keeps
    # NFHS districts with zero matched facilities and facilities without an NFHS match.
    need = (add_need_score(nfhs, capability)
            .withColumn("s_key", _norm_state(F.col("state")))
            .withColumn("d_key", _norm(F.col("district")))
            .groupBy("s_key", "d_key")
            .agg(F.first("state", ignorenulls=True).alias("need_state"),
                 F.first("district", ignorenulls=True).alias("need_district"),
                 F.round(F.avg("need_score"), 2).alias("need_score"),
                 F.max("n_indicators").alias("n_indicators")))
    supply = (supply
              .withColumn("s_key", _norm_state(F.col("state")))
              .withColumn("d_key", _norm(F.col("district")))
              .withColumnRenamed("state", "supply_state")
              .withColumnRenamed("district", "supply_district"))
    out = supply.join(need, ["s_key", "d_key"], "full")
    out = (out
           .withColumn("state", F.coalesce("supply_state", "need_state"))
           .withColumn("district", F.coalesce("supply_district", "need_district"))
           .drop("s_key", "d_key", "supply_state", "supply_district",
                 "need_state", "need_district"))

    for column in ("n_records", "n_candidates", "claiming", "corroborated", "n_indicators"):
        out = out.withColumn(column, F.coalesce(F.col(column), F.lit(0)).cast("long"))
    for column in ("trust_weighted_supply", "coverage", "knowledge", "mean_source_trust"):
        out = out.withColumn(column, F.coalesce(F.col(column), F.lit(0.0)).cast("double"))

    out = out.withColumn(
        "data_confidence",
        F.when(F.col("n_records") >= MIN_SOLID, "solid")
         .when(F.col("n_records") >= MIN_THIN, "thin")
         .otherwise("data_desert"))
    out = out.withColumn(
        "verdict",
        F.when(F.col("data_confidence") == "data_desert", "data_desert")
         .when(F.col("coverage") >= COVERAGE_OK, "covered")
         .when(F.col("need_score").isNull(), "underserved_need_unknown")
         .when(F.col("need_score") >= NEED_HI, "medical_desert")
         .otherwise("watch"))
    return out.select(
        "state", "district", "lat", "lon", "n_records", "n_candidates",
        "claiming", "corroborated", "trust_weighted_supply", "coverage",
        "knowledge", "mean_source_trust", "need_score", "n_indicators",
        "data_confidence", "verdict")


def build_district_table(fac: DataFrame, pincodes: DataFrame, nfhs: DataFrame,
                         capability: str, source_field: str = "source_urls",
                         combine_mode: str = "product") -> DataFrame:
    """The final function: raw tables + capability -> map-ready district table."""
    scored_geo = build_facility_table(
        fac, pincodes, capability, source_field=source_field, combine_mode=combine_mode)
    return build_district_from_scored(scored_geo, nfhs, capability)


def rank_deserts(district_table: DataFrame) -> DataFrame:
    """Highest-risk medical deserts first — feeds the dashboard's ranked list."""
    return (district_table
            .where(F.col("verdict").isin("medical_desert", "underserved_need_unknown"))
            .withColumn("risk_score",
                        F.round(F.coalesce(F.col("need_score"), F.lit(NEED_HI))
                                / (1.0 + F.col("trust_weighted_supply")), 2))
            .orderBy(F.desc("risk_score")))
