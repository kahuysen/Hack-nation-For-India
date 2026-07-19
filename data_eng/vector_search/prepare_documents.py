"""Export one semantic-search document per facility from Databricks SQL."""

import argparse
import hashlib
import re
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .config import settings
from .contracts import DOCUMENT_COLUMNS, validate_unique_ids
from .local_databricks import query_rows


SOURCE_FIELDS = [
    ("Facility", "name"),
    ("Facility type", "facility_type"),
    ("Capabilities", "capability"),
    ("Specialties", "specialties"),
    ("Procedures", "procedure"),
    ("Equipment", "equipment"),
    ("Description", "description"),
]


def _clean(value) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def build_document(row: dict) -> dict:
    sections = []
    for label, field in SOURCE_FIELDS:
        value = _clean(row.get(field))
        if value:
            sections.append(f"{label}: {value}")
    text = "\n".join(sections)
    facility_id = _clean(row.get("facility_id"))
    if not facility_id:
        facility_id = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "document_id": facility_id,
        "facility_id": facility_id,
        "name": _clean(row.get("name")) or "Unnamed facility",
        "state": _clean(row.get("state")) or "Unknown",
        "district": _clean(row.get("district")) or "Unknown",
        "facility_type": _clean(row.get("facility_type")),
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
        "source_urls": _clean(row.get("source_urls")),
        "document_text": text,
        "document_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def source_query(limit: int | None = None) -> str:
    limit_sql = f"LIMIT {int(limit)}" if limit else ""
    return f"""
        WITH geo AS (
          SELECT facility_id,
                 first(state, true) AS state,
                 first(district, true) AS district
          FROM {settings.facility_scores_table}
          GROUP BY facility_id
        ), source AS (
          SELECT *, row_number() OVER (PARTITION BY unique_id ORDER BY unique_id) AS row_number
          FROM {settings.source_table}
        )
        SELECT cast(source.unique_id AS string) AS facility_id,
               source.name,
               coalesce(geo.state, source.address_stateOrRegion) AS state,
               coalesce(geo.district, source.address_city, source.area) AS district,
               source.facilityTypeId AS facility_type,
               source.capability,
               source.specialties,
               source.procedure,
               source.equipment,
               source.description,
               source.latitude,
               source.longitude,
               source.source_urls
        FROM source
        LEFT JOIN geo ON cast(source.unique_id AS string) = geo.facility_id
        WHERE source.row_number = 1
        ORDER BY facility_id
        {limit_sql}
    """


def export_documents(profile: str, output: Path, limit: int | None = None) -> int:
    documents = [build_document(row) for row in query_rows(source_query(limit), profile)]
    if not documents:
        raise RuntimeError("The Databricks source query returned no facilities")
    validate_unique_ids(item["document_id"] for item in documents)
    output.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(documents).select(DOCUMENT_COLUMNS)
    pq.write_table(table, output, compression="zstd")
    return len(documents)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="codex")
    parser.add_argument("--output", type=Path, default=settings.documents_path)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    count = export_documents(args.profile, args.output, args.limit)
    print(f"Wrote {count} facility documents to {args.output}")


if __name__ == "__main__":
    main()
