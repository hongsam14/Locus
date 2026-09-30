"""knowledge router — canonical region knowledge (external NPC consumers, editor). No auth (MVP)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.deps import get_knowledge, get_localization
from api.errors import http_error
from api.schemas import QueryResultOut, localize_query_result
from locus.knowledge.wiring import KnowledgeContainer
from locus.localization.wiring import LocalizationContainer
from locus.shared.models import RegionBrief, RegionDiff

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/worlds/{world_id}/regions/{region_id}", response_model=QueryResultOut)
def region_knowledge(
    world_id: str,
    region_id: str,
    include_hearsay: bool = Query(True),
    k: KnowledgeContainer = Depends(get_knowledge),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> QueryResultOut:
    try:
        result = k.query.knowledge_for_region(world_id, region_id, include_hearsay=include_hearsay)
    except LookupError as exc:
        raise http_error(exc) from exc
    return localize_query_result(result, loc)


@router.get("/worlds/{world_id}/diff", response_model=RegionDiff)
def region_diff(
    world_id: str,
    region_a: str = Query(...),
    region_b: str = Query(...),
    k: KnowledgeContainer = Depends(get_knowledge),
) -> RegionDiff:
    try:
        return k.query.diff_regions(world_id, region_a, region_b)
    except LookupError as exc:
        raise http_error(exc) from exc


@router.get("/worlds/{world_id}/briefs", response_model=list[RegionBrief])
def region_briefs(
    world_id: str,
    top_k: int = Query(3, ge=0, le=20),
    k: KnowledgeContainer = Depends(get_knowledge),
) -> list[RegionBrief]:
    """Prompt-ready region summaries (event suggestion context, FR-D2 / BR-U2-20)."""
    try:
        return k.query.region_briefs(world_id, top_k=top_k)
    except LookupError as exc:
        raise http_error(exc) from exc
