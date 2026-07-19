"""Idempotently create and synchronize the Databricks AI Search resources."""

import argparse

from databricks.sdk.errors import NotFound
from databricks.sdk.service.vectorsearch import (
    DeltaSyncVectorIndexSpecRequest,
    EmbeddingVectorColumn,
    EndpointType,
    PipelineType,
    VectorIndexType,
)

from .config import settings
from .contracts import DOCUMENT_COLUMNS
from .local_databricks import workspace_client


def provision(profile: str) -> dict:
    client = workspace_client(profile)
    try:
        endpoint = client.vector_search_endpoints.get_endpoint(settings.endpoint_name)
    except NotFound:
        endpoint = client.vector_search_endpoints.create_endpoint(
            settings.endpoint_name, EndpointType.STANDARD
        ).result()

    try:
        index = client.vector_search_indexes.get_index(settings.index_name)
        created = False
    except NotFound:
        spec = DeltaSyncVectorIndexSpecRequest(
            source_table=settings.delta_table,
            pipeline_type=PipelineType.TRIGGERED,
            embedding_vector_columns=[
                EmbeddingVectorColumn(
                    name="embedding",
                    embedding_dimension=settings.embedding_dimension,
                )
            ],
            columns_to_sync=DOCUMENT_COLUMNS,
        )
        index = client.vector_search_indexes.create_index(
            name=settings.index_name,
            endpoint_name=settings.endpoint_name,
            primary_key="document_id",
            index_type=VectorIndexType.DELTA_SYNC,
            delta_sync_index_spec=spec,
        )
        created = True
    client.vector_search_indexes.sync_index(settings.index_name)
    return {
        "endpoint": settings.endpoint_name,
        "endpoint_state": endpoint.endpoint_status.state.value
        if endpoint.endpoint_status and endpoint.endpoint_status.state
        else None,
        "index": settings.index_name,
        "created": created,
        "index_status": index.status.detailed_state if index.status else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="codex")
    args = parser.parse_args()
    print(provision(args.profile))


if __name__ == "__main__":
    main()
