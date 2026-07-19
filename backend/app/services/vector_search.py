"""Local BGE query embedding and Databricks AI Search access."""

import json
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from databricks.sdk import WorkspaceClient

from ..config import settings


RESULT_COLUMNS = [
    "document_id",
    "facility_id",
    "name",
    "state",
    "district",
    "facility_type",
    "latitude",
    "longitude",
    "source_urls",
    "document_text",
]


@lru_cache(maxsize=1)
def embedding_model():
    from fastembed import TextEmbedding

    return TextEmbedding(
        model_name=settings.embedding_model,
        cache_dir=settings.embedding_cache_dir,
    )


def embed_query(query: str) -> list[float]:
    vector = np.asarray(next(embedding_model().query_embed(query)), dtype=np.float32)
    if vector.shape != (settings.embedding_dimension,):
        raise ValueError(
            f"Query embedding has dimension {vector.shape}, expected "
            f"{settings.embedding_dimension}"
        )
    norm = float(np.linalg.norm(vector))
    if norm:
        vector /= norm
    return vector.tolist()


def _cli_token(profile: str) -> str:
    local = Path.cwd() / "databricks.exe"
    executable = str(local) if local.exists() else shutil.which("databricks")
    if not executable:
        raise RuntimeError("Databricks CLI was not found")
    result = subprocess.run(
        [executable, "auth", "token", profile, "--output", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)["access_token"]


def workspace_client() -> WorkspaceClient:
    if settings.local_profile:
        return WorkspaceClient(
            host=settings.workspace_host,
            token=_cli_token(settings.local_profile),
            auth_type="pat",
        )
    return WorkspaceClient()


def _response_rows(response) -> list[dict]:
    payload = response.as_dict()
    manifest_columns = [
        column["name"] for column in payload.get("manifest", {}).get("columns", [])
    ]
    rows = []
    for values in payload.get("result", {}).get("data_array", []) or []:
        if len(values) == len(manifest_columns) + 1:
            data = dict(zip(manifest_columns, values[:-1]))
            data["similarity_score"] = values[-1]
        else:
            data = dict(zip(manifest_columns, values))
            score = data.pop("score", data.pop("_score", None))
            data["similarity_score"] = score
        rows.append(data)
    return rows


def similarity_search(
    query: str,
    state: str | None = None,
    district: str | None = None,
    limit: int = 10,
) -> list[dict]:
    filters = {}
    if state:
        filters["state"] = state
    if district:
        filters["district"] = district
    response = workspace_client().vector_search_indexes.query_index(
        index_name=settings.vector_index,
        columns=RESULT_COLUMNS,
        query_vector=embed_query(query),
        num_results=limit,
        filters_json=json.dumps(filters) if filters else None,
    )
    return _response_rows(response)
