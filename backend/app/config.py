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
    local_profile: str | None = os.getenv("DATABRICKS_CONFIG_PROFILE")


settings = Settings()
