"""World editor routes (U3, BLM §7 〔Step 1.3 정정〕) under ``/api/world``.

Edits go through the editor classes (``WorldContainer.editors``): replace writes,
checked references, search documents and the cache handled by them. Error mapping:
``LookupError`` 404, ``ValueError`` 400 (incl. path/body mismatch), a region where an
open session's player stands 409 with those session ids (Q2=A).
"""

from __future__ import annotations

from contextlib import ExitStack

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from api.deps import display_lang, get_localization, get_play_optional, get_world
from api.errors import http_error
from api.schemas import (
    ConnectionSave,
    EditorRegionViewOut,
    LocalizedKnowledge,
    PriorRefsOut,
    ScopesIn,
    localize_editor_view,
    localize_knowledge,
    purge_translations,
)
from locus.localization.wiring import LocalizationContainer
from locus.play.errors import TurnInProgressError
from locus.play.wiring import PlayContainer
from locus.shared.models import NPC, ConnectionEdge, ConnectionKind, Knowledge, Region, WikiPrior
from locus.world.editor import (
    ConnectionKey,
    Editors,
    RegionDeletePlan,
    RegionDeleteReport,
    RegionInUseError,
)
from locus.world.editor.writes import check_path
from locus.world.npc_drafts import NpcDraftResult
from locus.world.wiring import WorldContainer

router = APIRouter(tags=["world-editor"])
_ERRORS = (LookupError, ValueError)


def _editors(w: WorldContainer) -> Editors:
    if w.editors is None:
        raise HTTPException(status_code=503, detail="world editor unavailable")
    return w.editors


# --- regions -------------------------------------------------------------- #
@router.get("/worlds/{world_id}/regions/{region_id}/editor", response_model=EditorRegionViewOut)
def editor_region(
    world_id: str,
    region_id: str,
    w: WorldContainer = Depends(get_world),
    loc: LocalizationContainer | None = Depends(get_localization),
    lang: str = Depends(display_lang),
) -> EditorRegionViewOut:
    try:
        view = _editors(w).regions.editor_view(world_id, region_id)
    except _ERRORS as exc:
        raise http_error(exc) from exc
    return localize_editor_view(view, loc, lang=lang)


@router.post("/worlds/{world_id}/regions", response_model=Region, status_code=201)
def create_region(world_id: str, region: Region, w: WorldContainer = Depends(get_world)) -> Region:
    try:
        check_path(world_id, None, region.world_id, region.id)
        return _editors(w).regions.create_region(region)
    except _ERRORS as exc:
        raise http_error(exc) from exc


@router.put("/worlds/{world_id}/regions/{region_id}", response_model=Region)
def upsert_region(
    world_id: str, region_id: str, region: Region, w: WorldContainer = Depends(get_world)
) -> Region:
    """A replace write: a cleared field is gone (BR-U3-1); a new parent is checked for
    cycles (BR-U3-7)."""
    try:
        check_path(world_id, region_id, region.world_id, region.id)
        return _editors(w).regions.upsert_region(region)
    except _ERRORS as exc:
        raise http_error(exc) from exc


def _protected(world_id: str, play: PlayContainer | None) -> dict[str, list[str]]:
    return play.sessions.open_player_regions(world_id) if play is not None else {}


@router.get("/worlds/{world_id}/regions/{region_id}/delete-plan", response_model=RegionDeletePlan)
def region_delete_plan(
    world_id: str,
    region_id: str,
    w: WorldContainer = Depends(get_world),
    play: PlayContainer | None = Depends(get_play_optional),
) -> RegionDeletePlan:
    """What a delete would do, and the sessions that block it (shown before, BR-U3-9/16).
    A read without leases: the delete itself checks again under them."""
    try:
        plan = _editors(w).regions.plan_region_delete(world_id, region_id)
    except _ERRORS as exc:
        raise http_error(exc) from exc
    return plan.model_copy(
        update={"blocked_by_sessions": _protected(world_id, play).get(region_id, [])}
    )


@router.delete("/worlds/{world_id}/regions/{region_id}", response_model=RegionDeleteReport)
def delete_region(
    world_id: str,
    region_id: str,
    w: WorldContainer = Depends(get_world),
    play: PlayContainer | None = Depends(get_play_optional),
) -> RegionDeleteReport:
    """Q1=A tidy delete. The GM lease of every open session of the world is held over
    the check and the delete, so no move lands in between; a session mid-turn is 409
    (BR-U3-16). A session started meanwhile is a known limit (code-summary)."""
    regions = _editors(w).regions
    with ExitStack() as leases:
        if play is not None:
            for session in sorted(play.sessions.open_sessions(world_id), key=lambda s: s.id):
                try:
                    leases.enter_context(play.guard.hold(session.id, label="editor"))
                except TurnInProgressError as exc:  # the stack releases what it holds
                    raise http_error(exc) from exc
        try:
            return regions.delete_region(world_id, region_id, protected=_protected(world_id, play))
        except RegionInUseError as exc:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "a player of an open session stands in this region",
                    "session_ids": exc.session_ids,
                },
            ) from exc
        except _ERRORS as exc:
            raise http_error(exc) from exc


# --- connections ------------------------------------------------------------ #
@router.put("/worlds/{world_id}/connections", response_model=list[ConnectionEdge])
def save_connection(
    world_id: str, body: ConnectionSave, w: WorldContainer = Depends(get_world)
) -> list[ConnectionEdge]:
    """Save a pair (BR-U3-10); with ``previous_kind`` it is a kind change (BR-U3-11)
    and only the kind changes: the pair keeps its weight, rationale, prior ref and
    provenance, and the rest of the body is not written over them (U3 review #3)."""
    connections = _editors(w).connections
    edge = ConnectionEdge(**body.model_dump(exclude={"previous_kind"}))
    try:
        check_path(world_id, None, edge.world_id, "")
        if body.previous_kind is not None and str(body.previous_kind) != str(edge.kind):
            key = ConnectionKey(
                world_id=world_id,
                a_region_id=edge.source_region_id,
                b_region_id=edge.target_region_id,
                kind=body.previous_kind,
            )
            return connections.change_connection_kind(key, edge.kind)
        return connections.upsert_connection(edge)
    except _ERRORS as exc:
        raise http_error(exc) from exc


@router.delete("/worlds/{world_id}/connections")
def delete_connection(
    world_id: str,
    a: str,
    b: str,
    kind: ConnectionKind,
    w: WorldContainer = Depends(get_world),
) -> dict[str, int]:
    key = ConnectionKey(world_id=world_id, a_region_id=a, b_region_id=b, kind=kind)
    try:
        return {"deleted": _editors(w).connections.delete_connection(key)}
    except _ERRORS as exc:
        raise http_error(exc) from exc


# --- knowledge and scopes ------------------------------------------------- #
@router.post(
    "/worlds/{world_id}/regions/{region_id}/knowledge", response_model=Knowledge, status_code=201
)
def create_knowledge(
    world_id: str, region_id: str, knowledge: Knowledge, w: WorldContainer = Depends(get_world)
) -> Knowledge:
    """ "지식 추가": the item plus one DIRECT scope here (BR-U3-12)."""
    try:
        check_path(world_id, None, knowledge.world_id, knowledge.id)
        return _editors(w).knowledge.create_knowledge(knowledge, region_id)
    except _ERRORS as exc:
        raise http_error(exc) from exc


@router.put("/worlds/{world_id}/knowledge/{knowledge_id}", response_model=Knowledge)
def upsert_knowledge(
    world_id: str, knowledge_id: str, knowledge: Knowledge, w: WorldContainer = Depends(get_world)
) -> Knowledge:
    """A replace write; scopes stay (US-2.3)."""
    try:
        check_path(world_id, knowledge_id, knowledge.world_id, knowledge.id)
        return _editors(w).knowledge.upsert_knowledge(knowledge)
    except _ERRORS as exc:
        raise http_error(exc) from exc


@router.put("/worlds/{world_id}/knowledge/{knowledge_id}/scopes")
def set_scopes(
    world_id: str, knowledge_id: str, body: ScopesIn, w: WorldContainer = Depends(get_world)
) -> dict[str, list[str]]:
    try:
        ids = _editors(w).knowledge.set_scopes(world_id, knowledge_id, body.region_ids)
    except _ERRORS as exc:
        raise http_error(exc) from exc
    return {"region_ids": ids}


@router.delete("/worlds/{world_id}/knowledge/{knowledge_id}", status_code=204)
def delete_knowledge(
    world_id: str,
    knowledge_id: str,
    w: WorldContainer = Depends(get_world),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> Response:
    """Node, search document, then its translations (BR-U3-3)."""
    try:
        _editors(w).knowledge.delete_knowledge(world_id, knowledge_id)
    except _ERRORS as exc:
        raise http_error(exc) from exc
    purge_translations(loc, kind="knowledge", ids=[knowledge_id])
    return Response(status_code=204)


@router.get("/worlds/{world_id}/knowledge/unscoped", response_model=list[LocalizedKnowledge])
def list_unscoped(
    world_id: str,
    w: WorldContainer = Depends(get_world),
    loc: LocalizationContainer | None = Depends(get_localization),
    lang: str = Depends(display_lang),
) -> list[LocalizedKnowledge]:
    try:
        items = _editors(w).knowledge.list_unscoped(world_id)
    except _ERRORS as exc:
        raise http_error(exc) from exc
    return localize_knowledge(items, loc, world_id=world_id, lang=lang)


# --- NPCs ------------------------------------------------------------------- #
@router.post("/worlds/{world_id}/npcs", response_model=NPC, status_code=201)
def create_npc(world_id: str, npc: NPC, w: WorldContainer = Depends(get_world)) -> NPC:
    try:
        check_path(world_id, None, npc.world_id, npc.id)
        return _editors(w).npcs.create_npc(npc)
    except _ERRORS as exc:
        raise http_error(exc) from exc


@router.put("/worlds/{world_id}/npcs/{npc_id}", response_model=NPC)
def upsert_npc(world_id: str, npc_id: str, npc: NPC, w: WorldContainer = Depends(get_world)) -> NPC:
    try:
        check_path(world_id, npc_id, npc.world_id, npc.id)
        return _editors(w).npcs.upsert_npc(npc)
    except _ERRORS as exc:
        raise http_error(exc) from exc


@router.delete("/worlds/{world_id}/npcs/{npc_id}", status_code=204)
def delete_npc(world_id: str, npc_id: str, w: WorldContainer = Depends(get_world)) -> Response:
    """Conversations with the NPC stay in their sessions (BR-U3-17)."""
    try:
        _editors(w).npcs.delete_npc(world_id, npc_id)
    except _ERRORS as exc:
        raise http_error(exc) from exc
    return Response(status_code=204)


@router.post("/worlds/{world_id}/regions/{region_id}/npc-drafts", response_model=NpcDraftResult)
def npc_drafts(
    world_id: str,
    region_id: str,
    n: int = Query(default=3),
    w: WorldContainer = Depends(get_world),
) -> NpcDraftResult:
    """0–3 drafts from one LLM call, nothing stored (BR-U3-20/21); 503 without an LLM."""
    if w.npc_drafts is None:
        raise HTTPException(status_code=503, detail="NPC drafts need an LLM provider")
    try:
        return w.npc_drafts.suggest(world_id, region_id, n=n)
    except _ERRORS as exc:
        raise http_error(exc) from exc


# --- wiki evidence ------------------------------------------------------------ #
def _wiki(w: WorldContainer):
    if w.wiki_admin is None:
        raise HTTPException(status_code=503, detail="wiki admin unavailable")
    return w.wiki_admin


@router.get("/worlds/{world_id}/priors", response_model=list[WikiPrior])
def list_priors(world_id: str, w: WorldContainer = Depends(get_world)) -> list[WikiPrior]:
    return _wiki(w).list_priors(world_id)


@router.get("/worlds/{world_id}/prior-refs", response_model=PriorRefsOut)
def prior_refs(world_id: str, w: WorldContainer = Depends(get_world)) -> PriorRefsOut:
    """Each prior with what cites it, and cited ids the world lacks (BR-U3-31)."""
    admin = _wiki(w)
    try:
        return PriorRefsOut(usages=admin.prior_refs(world_id), broken=admin.broken_refs(world_id))
    except _ERRORS as exc:
        raise http_error(exc) from exc


@router.delete("/worlds/{world_id}/priors/{prior_id}", status_code=204)
def delete_prior(world_id: str, prior_id: str, w: WorldContainer = Depends(get_world)) -> Response:
    try:
        _wiki(w).delete_prior(world_id, prior_id)
    except _ERRORS as exc:
        raise http_error(exc) from exc
    return Response(status_code=204)
