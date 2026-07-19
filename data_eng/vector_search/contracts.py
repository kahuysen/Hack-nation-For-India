"""Column names and validation shared across vector-search pipeline stages."""

DOCUMENT_COLUMNS = [
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
    "document_hash",
]
EMBEDDING_COLUMN = "embedding"
INDEX_COLUMNS = [*DOCUMENT_COLUMNS, EMBEDDING_COLUMN]


def require_columns(actual: list[str], required: list[str], stage: str) -> None:
    missing = sorted(set(required) - set(actual))
    if missing:
        raise ValueError(f"{stage} is missing required columns: {', '.join(missing)}")


def validate_unique_ids(values) -> None:
    ids = [str(value).strip() for value in values]
    if any(not value for value in ids):
        raise ValueError("document_id must be non-empty")
    if len(ids) != len(set(ids)):
        raise ValueError("document_id must be unique")
