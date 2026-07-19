"""Databricks SQL connectivity for deployed and local execution."""

import json
import math
import shutil
import subprocess
from pathlib import Path

from databricks import sql
from databricks.sdk.core import Config

from .config import settings


def connection():
    if settings.local_profile:
        local_cli = Path.cwd() / "databricks.exe"
        cli = str(local_cli) if local_cli.exists() else shutil.which("databricks")
        if not cli:
            raise RuntimeError("Databricks CLI not found for local profile authentication")
        token_result = subprocess.run(
            [cli, "auth", "token", settings.local_profile, "--output", "json"],
            check=True,
            capture_output=True,
            text=True,
        )
        token = json.loads(token_result.stdout)["access_token"]
        return sql.connect(
            server_hostname=settings.workspace_host.removeprefix("https://"),
            http_path=f"/sql/1.0/warehouses/{settings.warehouse_id}",
            access_token=token,
        )

    config = Config()
    return sql.connect(
        server_hostname=config.host.removeprefix("https://"),
        http_path=f"/sql/1.0/warehouses/{settings.warehouse_id}",
        # The SQL connector first calls the provider to obtain a callable
        # header factory, then calls that factory for each request.
        credentials_provider=lambda: config.authenticate,
    )


def query_rows(statement: str, parameters: list | None = None) -> list[dict]:
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(statement, parameters or [])
            columns = [item[0] for item in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


def clean_row(row: dict) -> dict:
    return {
        key: None if isinstance(value, float) and math.isnan(value) else value
        for key, value in row.items()
    }
