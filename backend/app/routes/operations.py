"""Operational readiness routes."""

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..database import query_rows

router = APIRouter(prefix="/api", tags=["Operations"])


@router.get("/health", summary="Check API and pipeline readiness")
def health():
    try:
        rows = query_rows(
            f"SELECT (SELECT count(*) FROM {settings.facility_table}) AS facility_scores, "
            f"(SELECT count(*) FROM {settings.district_table}) AS district_scores"
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Materialized scoring tables are unavailable") from exc
    return {
        "status": "ok",
        **rows[0],
        "facility_table": settings.facility_table,
        "district_table": settings.district_table,
    }
