"""FastAPI application assembly and optional React static hosting."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .routes import evidence, locations, operations, planning, search

app = FastAPI(
    title="Medical Desert Planner API",
    version="2.0.0",
    summary="Track 2 backend for evidence-weighted healthcare gap planning.",
    description=(
        "Serves batch-computed facility trust, source provenance, NFHS-5 need, "
        "and district medical-desert classifications from Unity Catalog tables."
    ),
)
app.include_router(operations.router)
app.include_router(planning.router)
app.include_router(evidence.router)
app.include_router(locations.router)
app.include_router(search.router)

frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
else:
    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/docs")
