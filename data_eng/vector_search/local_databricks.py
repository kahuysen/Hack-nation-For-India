"""Local CLI OAuth helpers without persisting or printing access tokens."""

import json
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path

from databricks import sql
from databricks.sdk import WorkspaceClient

from .config import settings


def cli_executable() -> str:
    local = Path.cwd() / "databricks.exe"
    executable = str(local) if local.exists() else shutil.which("databricks")
    if not executable:
        raise RuntimeError("Databricks CLI was not found")
    return executable


def cli_token(profile: str) -> str:
    result = subprocess.run(
        [cli_executable(), "auth", "token", profile, "--output", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)["access_token"]


@contextmanager
def sql_connection(profile: str):
    connection = sql.connect(
        server_hostname=settings.workspace_host.removeprefix("https://"),
        http_path=f"/sql/1.0/warehouses/{settings.warehouse_id}",
        access_token=cli_token(profile),
    )
    try:
        yield connection
    finally:
        connection.close()


def query_rows(statement: str, profile: str) -> list[dict]:
    with sql_connection(profile) as connection:
        with connection.cursor() as cursor:
            cursor.execute(statement)
            if not cursor.description:
                return []
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]


def workspace_client(profile: str) -> WorkspaceClient:
    return WorkspaceClient(host=settings.workspace_host, token=cli_token(profile))
