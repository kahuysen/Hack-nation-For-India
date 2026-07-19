"""Shared vector-search contract for local, Spark, and API execution."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VectorSearchSettings:
    workspace_host: str = os.getenv(
        "DATABRICKS_WORKSPACE_HOST",
        "https://dbc-1aa1c463-f7d2.cloud.databricks.com",
    )
    warehouse_id: str = os.getenv("DATABRICKS_WAREHOUSE_ID", "8629e2ec9fce0130")
    source_table: str = os.getenv(
        "VECTOR_SOURCE_TABLE",
        "databricks_virtue_foundation_dataset_dais_2026."
        "virtue_foundation_dataset.facilities",
    )
    facility_scores_table: str = os.getenv(
        "FACILITY_SCORES_TABLE", "workspace.default.facility_capability_scores"
    )
    volume_name: str = os.getenv(
        "VECTOR_STAGING_VOLUME", "workspace.default.vector_ingest"
    )
    delta_table: str = os.getenv(
        "VECTOR_SOURCE_DELTA_TABLE", "workspace.default.facility_evidence_embeddings"
    )
    endpoint_name: str = os.getenv("VECTOR_SEARCH_ENDPOINT", "medical-desert-search")
    index_name: str = os.getenv(
        "VECTOR_SEARCH_INDEX",
        "workspace.default.facility_evidence_embeddings_index",
    )
    model_name: str = os.getenv(
        "VECTOR_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"
    )
    embedding_dimension: int = int(os.getenv("VECTOR_EMBEDDING_DIMENSION", "384"))
    artifact_directory: Path = Path(
        os.getenv("VECTOR_ARTIFACT_DIR", ".artifacts/vector_search")
    )

    @property
    def documents_path(self) -> Path:
        return self.artifact_directory / "facility_documents.parquet"

    @property
    def embeddings_path(self) -> Path:
        return self.artifact_directory / "facility_embeddings.parquet"

    @property
    def volume_path(self) -> str:
        return f"/Volumes/{self.volume_name.replace('.', '/')}"

    @property
    def staged_embeddings_path(self) -> str:
        return f"{self.volume_path}/facility_embeddings.parquet"


settings = VectorSearchSettings()
