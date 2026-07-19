"""Facility-level evidence routes."""

import json

from fastapi import APIRouter, Query

from ..config import settings
from ..database import clean_row, query_rows
from ..dependencies import capability_id
from ..models import FacilityEvidence

router = APIRouter(prefix="/api", tags=["Evidence"])


@router.get("/facilities", response_model=list[FacilityEvidence])
def facility_evidence(
    capability: str = Query(..., examples=["emergency"]),
    state: str | None = None,
    district: str | None = None,
    candidates_only: bool = True,
    limit: int = Query(100, ge=1, le=500),
):
    """Return precomputed facility evidence behind the district classification."""
    resolved_id = capability_id(capability)
    clauses, parameters = ["capability_id = ?"], [resolved_id]
    if state:
        clauses.append("lower(state) = lower(?)")
        parameters.append(state)
    if district:
        clauses.append("lower(district) = lower(?)")
        parameters.append(district)
    if candidates_only:
        clauses.append("is_candidate = 1")
    parameters.append(limit)
    rows = query_rows(
        f"SELECT * FROM {settings.facility_table} WHERE {' AND '.join(clauses)} "
        "ORDER BY trust_weight DESC, knowledge DESC LIMIT ?",
        parameters,
    )
    results = []
    for raw_row in rows:
        row = clean_row(raw_row)
        raw_evidence = json.loads(row.pop("evidence_json") or "[]")
        row["evidence"] = [
            item for item in raw_evidence if item.get("snippet") and item["snippet"].strip()
        ]
        results.append(row)
    return results
