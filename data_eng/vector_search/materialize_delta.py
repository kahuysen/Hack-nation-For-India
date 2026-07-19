"""Materialize staged embedding Parquet as a managed, CDF-enabled Delta table."""

from .config import settings
from .contracts import INDEX_COLUMNS


def materialize_embeddings(
    spark,
    staged_path: str = settings.staged_embeddings_path,
    table_name: str = settings.delta_table,
) -> dict:
    from pyspark.sql import functions as F

    frame = spark.read.parquet(staged_path)
    missing = sorted(set(INDEX_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"Staged embeddings are missing: {', '.join(missing)}")
    duplicates = frame.groupBy("document_id").count().where("count > 1").limit(1).count()
    if duplicates:
        raise ValueError("document_id must be unique before Delta materialization")
    frame = frame.select(
        *[F.col(column) for column in INDEX_COLUMNS if column != "embedding"],
        F.col("embedding").cast("array<float>").alias("embedding"),
    )
    (frame.write.mode("overwrite")
     .option("overwriteSchema", "true")
     .saveAsTable(table_name))
    spark.sql(
        f"ALTER TABLE {table_name} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)"
    )
    return {
        "table": table_name,
        "rows": frame.count(),
        "embedding_dimension": settings.embedding_dimension,
    }
