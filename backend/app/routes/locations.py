"""Facility location routes for the map of India."""

import logging

from fastapi import APIRouter

from ..config import settings
from ..database import clean_row, query_rows
from ..models import FacilityLocation

router = APIRouter(prefix="/api", tags=["Locations"])
logger = logging.getLogger(__name__)


@router.get("/facility-locations", response_model=list[FacilityLocation])
def facility_locations():
    """Return every geolocated facility (all types) as slim map-ready rows.

    Returns an empty list instead of failing when the materialized table does
    not exist yet, so a deploy ahead of the pipeline run degrades gracefully.
    """
    try:
        rows = query_rows(
            "SELECT facility_id, name, facility_type, state, district, latitude, longitude "
            f"FROM {settings.locations_table}"
        )
    except Exception:
        logger.warning(
            "facility locations table %s unavailable; returning empty list",
            settings.locations_table,
        )
        return []
    return [clean_row(row) for row in rows]
