"""Environment-backed application configuration."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    warehouse_id: str = os.getenv("DATABRICKS_WAREHOUSE_ID", "8629e2ec9fce0130")
    workspace_host: str = os.getenv(
        "DATABRICKS_WORKSPACE_HOST", "https://dbc-1aa1c463-f7d2.cloud.databricks.com")
    facility_table: str = os.getenv(
        "FACILITY_SCORES_TABLE", "workspace.default.facility_capability_scores")
    district_table: str = os.getenv(
        "DISTRICT_SCORES_TABLE", "workspace.default.district_capability_scores")
    vector_index: str = os.getenv(
        "VECTOR_SEARCH_INDEX",
        "workspace.default.facility_evidence_embeddings_index")
    embedding_model: str = os.getenv(
        "VECTOR_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    embedding_dimension: int = int(os.getenv("VECTOR_EMBEDDING_DIMENSION", "384"))
    embedding_cache_dir: str = os.getenv(
        "VECTOR_EMBEDDING_CACHE_DIR", "/tmp/fastembed_cache")
    local_profile: str | None = os.getenv("DATABRICKS_CONFIG_PROFILE")


settings = Settings()
