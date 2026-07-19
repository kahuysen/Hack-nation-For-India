"""Semantic facility-evidence search routes."""

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..models import SimilaritySearchRequest, SimilaritySearchResponse
from ..services.vector_search import similarity_search

router = APIRouter(prefix="/api", tags=["Search"])


@router.post("/search", response_model=SimilaritySearchResponse)
def search_facilities(request: SimilaritySearchRequest):
    """Search facility evidence with locally generated BGE embeddings."""
    try:
        results = similarity_search(
            request.query,
            state=request.state,
            district=request.district,
            limit=request.limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="The facility evidence search index is unavailable",
        ) from exc
    return {"query": request.query, "model": settings.embedding_model, "results": results}
