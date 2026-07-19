"""Capability and district-planning routes."""

from fastapi import APIRouter, Query

from data_eng.contracts import CAPABILITIES

from ..config import settings
from ..database import clean_row, query_rows
from ..dependencies import capability_id
from ..models import CapabilityList, RegionResult, Verdict

router = APIRouter(prefix="/api", tags=["Planning"])


@router.get("/capabilities", response_model=CapabilityList)
def list_capabilities():
    with_need = {"icu", "nicu", "emergency", "maternity", "oncology", "cardiac"}
    return {
        "capabilities": [
            {"id": item.id, "label": item.label, "has_need_signal": item.id in with_need}
            for item in CAPABILITIES
        ]
    }


@router.get("/regions", response_model=list[RegionResult])
def rank_regions(
    capability: str = Query(..., examples=["nicu"]),
    state: str | None = None,
    verdict: Verdict | None = None,
    limit: int = Query(50, ge=1, le=2000),
):
    """Rank districts using the materialized Spark pipeline's risk score."""
    resolved_id = capability_id(capability)
    clauses, parameters = ["capability_id = ?"], [resolved_id]
    if state:
        clauses.append("lower(state) = lower(?)")
        parameters.append(state)
    if verdict:
        clauses.append("verdict = ?")
        parameters.append(verdict)
    parameters.append(limit)
    rows = query_rows(
        f"SELECT * FROM {settings.district_table} WHERE {' AND '.join(clauses)} "
        "ORDER BY risk_score DESC, state, district LIMIT ?",
        parameters,
    )
    return [clean_row(row) for row in rows]
