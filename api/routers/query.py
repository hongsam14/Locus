"""Public serving router — region knowledge queries (U8, FR-H). No auth (MVP)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from locus.models import QueryResult, RegionDiff

router = APIRouter(prefix="/api/query", tags=["query"])


def _engine(request: Request):
    engine = getattr(request.app.state, "query_engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="query engine not configured")
    return engine


@router.get("/regions/{region_id}/knowledge", response_model=QueryResult)
def region_knowledge(
    region_id: str,
    request: Request,
    world_id: str = Query(...),
    include_rumors: bool = Query(True),
) -> QueryResult:
    try:
        return _engine(request).knowledge_for_region(
            world_id, region_id, include_rumors=include_rumors
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/diff", response_model=RegionDiff)
def region_diff(
    request: Request,
    world_id: str = Query(...),
    region_a: str = Query(...),
    region_b: str = Query(...),
) -> RegionDiff:
    try:
        return _engine(request).diff_regions(world_id, region_a, region_b)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
