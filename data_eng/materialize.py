"""Materialize teammate Spark scoring into stable Delta tables for FastAPI."""

from functools import reduce

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

try:
    from .contracts import CAPABILITIES
    from .district_rollup import build_district_from_scored, build_facility_table
except ImportError:  # direct execution from the data_eng directory in Databricks
    from contracts import CAPABILITIES
    from district_rollup import build_district_from_scored, build_facility_table


SOURCE_CATALOG = "databricks_virtue_foundation_dataset_dais_2026"
SOURCE_SCHEMA = "virtue_foundation_dataset"
OUTPUT_SCHEMA = "workspace.default"
FACILITY_OUTPUT = f"{OUTPUT_SCHEMA}.facility_capability_scores"
DISTRICT_OUTPUT = f"{OUTPUT_SCHEMA}.district_capability_scores"


def _union(frames: list[DataFrame]) -> DataFrame:
    return reduce(lambda left, right: left.unionByName(right, allowMissingColumns=True), frames)


def _facility_contract(scored: DataFrame, capability_id: str,
                       pipeline_key: str) -> DataFrame:
    evidence = F.array(
        F.struct(F.lit("capability").alias("field"), F.col("snippet_capability").alias("snippet")),
        F.struct(F.lit("procedure").alias("field"), F.col("snippet_procedure").alias("snippet")),
        F.struct(F.lit("equipment").alias("field"), F.col("snippet_equipment").alias("snippet")),
        F.struct(F.lit("description").alias("field"), F.col("snippet_description").alias("snippet")),
    )
    return scored.select(
        F.lit(capability_id).alias("capability_id"),
        F.lit(pipeline_key).alias("capability_key"),
        F.col("unique_id").cast("string").alias("facility_id"),
        F.coalesce(F.col("name").cast("string"), F.lit("Unnamed facility")).alias("name"),
        F.coalesce(F.col("state").cast("string"), F.lit("Unknown")).alias("state"),
        F.coalesce(F.col("district").cast("string"), F.lit("Unknown")).alias("district"),
        F.col("pincode").cast("string").alias("pin"),
        F.col("is_candidate").cast("int"),
        F.col("match_capability").cast("int").alias("claiming"),
        F.col("n_corroborating").cast("int"),
        F.col("trust_band").alias("tier"),
        F.col("facility_trust").cast("double").alias("trust_weight"),
        F.round(F.col("n_corrob_present") / F.lit(4.0), 3).alias("knowledge"),
        F.col("source_trust").cast("double"),
        F.col("data_confidence"),
        F.to_json(evidence).alias("evidence_json"),
        F.col("description").cast("string"),
        F.col("latitude").cast("double"),
        F.col("longitude").cast("double"),
        F.col("source_urls").cast("string"),
    )


def _district_contract(districts: DataFrame, capability_id: str,
                       pipeline_key: str) -> DataFrame:
    return districts.select(
        F.lit(capability_id).alias("capability_id"),
        F.lit(pipeline_key).alias("capability_key"),
        "state", "district", "lat", "lon", "n_records", "n_candidates",
        "claiming", "corroborated", "trust_weighted_supply", "coverage",
        "knowledge", "mean_source_trust", "need_score", "n_indicators",
        "data_confidence", "verdict",
    ).withColumn(
        "risk_score",
        F.round((F.coalesce(F.col("need_score"), F.lit(50.0)) / F.lit(100.0))
                * (F.lit(1.0) - F.col("coverage")) * F.col("knowledge"), 4),
    )


def materialize_all(spark, output_schema: str = OUTPUT_SCHEMA) -> dict:
    """Score all supported capabilities and overwrite the two API-facing tables."""
    source = f"{SOURCE_CATALOG}.{SOURCE_SCHEMA}"
    facilities = spark.table(f"{source}.facilities")
    pincodes = spark.table(f"{source}.india_post_pincode_directory")
    nfhs = spark.table(f"{source}.nfhs_5_district_health_indicators")

    facility_frames, district_frames = [], []
    for capability in CAPABILITIES:
        scored = build_facility_table(
            facilities, pincodes, capability.pipeline_key, source_field="source_urls")
        facility_frames.append(
            _facility_contract(scored, capability.id, capability.pipeline_key))
        district_frames.append(
            _district_contract(
                build_district_from_scored(scored, nfhs, capability.pipeline_key),
                capability.id,
                capability.pipeline_key,
            ))

    facility_output = f"{output_schema}.facility_capability_scores"
    district_output = f"{output_schema}.district_capability_scores"
    _union(facility_frames).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
        facility_output)
    _union(district_frames).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(
        district_output)
    return {"facility_table": facility_output, "district_table": district_output}
