"""Session router — GameSession lifecycle + timeline (S1) + rumor engine (S2).

S1: start / history / get / close / timeline (``session_service``).
S2: generate / regenerate / support / distortion / advance-turn (``game_master``)
and the NPC session query (``session_query``). Services injected via app.state.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from locus.models import QueryResult
from locus.session.game_master import SessionClosedError, TurnResult
from locus.session.models import GameSession, RegionDistortion, SessionRumor, TimelineEntry
from locus.session.service import WorldNotFoundError

router = APIRouter(prefix="/api/session", tags=["session"])


class SupportUpdate(BaseModel):
    support: float


class DistortionUpdate(BaseModel):
    degree: float


def _svc(request: Request, name: str = "session_service"):
    svc = getattr(request.app.state, name, None)
    if svc is None:
        raise HTTPException(status_code=503, detail=f"{name} not configured")
    return svc


def _session_error(exc: Exception) -> HTTPException:
    """Map service errors to HTTP status (404 missing, 409 closed)."""
    if isinstance(exc, SessionClosedError):
        return HTTPException(status_code=409, detail=str(exc))
    return HTTPException(status_code=404, detail=str(exc))


@router.post("/worlds/{world_id}/sessions", response_model=GameSession)
def start_session(world_id: str, request: Request) -> GameSession:
    try:
        return _svc(request).start_session(world_id)
    except WorldNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/worlds/{world_id}/sessions", response_model=list[GameSession])
def list_sessions(world_id: str, request: Request) -> list[GameSession]:
    return _svc(request).list_sessions(world_id)


@router.get("/sessions/{session_id}", response_model=GameSession)
def get_session(session_id: str, request: Request) -> GameSession:
    try:
        return _svc(request).get_session(session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/close", response_model=GameSession)
def close_session(session_id: str, request: Request) -> GameSession:
    try:
        return _svc(request).close_session(session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/timeline", response_model=list[TimelineEntry])
def get_timeline(session_id: str, request: Request) -> list[TimelineEntry]:
    try:
        return _svc(request).get_timeline(session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# --- S2: rumor engine ------------------------------------------------------- #
@router.get("/sessions/{session_id}/regions/{region_id}/rumors", response_model=list[SessionRumor])
def list_rumors(session_id: str, region_id: str, request: Request) -> list[SessionRumor]:
    try:
        return _svc(request, "game_master").list_rumors(session_id, region_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/regions/{region_id}/rumors", response_model=list[SessionRumor])
def generate_rumors(session_id: str, region_id: str, request: Request) -> list[SessionRumor]:
    try:
        return _svc(request, "game_master").generate_rumors(session_id, region_id)
    except (LookupError, SessionClosedError) as exc:
        raise _session_error(exc) from exc


@router.post(
    "/sessions/{session_id}/regions/{region_id}/rumors/regen", response_model=list[SessionRumor]
)
def regenerate_region(session_id: str, region_id: str, request: Request) -> list[SessionRumor]:
    try:
        return _svc(request, "game_master").regenerate_region(session_id, region_id)
    except (LookupError, SessionClosedError) as exc:
        raise _session_error(exc) from exc


@router.put("/sessions/{session_id}/rumors/{rumor_id}/support", response_model=SessionRumor)
def adjust_support(
    session_id: str, rumor_id: str, body: SupportUpdate, request: Request
) -> SessionRumor:
    try:
        return _svc(request, "game_master").adjust_support(session_id, rumor_id, body.support)
    except (LookupError, SessionClosedError) as exc:
        raise _session_error(exc) from exc


@router.put(
    "/sessions/{session_id}/regions/{region_id}/distortion", response_model=RegionDistortion
)
def set_distortion(
    session_id: str, region_id: str, body: DistortionUpdate, request: Request
) -> RegionDistortion:
    gm = _svc(request, "game_master")
    try:
        gm.set_region_distortion(session_id, region_id, body.degree)
    except (LookupError, SessionClosedError) as exc:
        raise _session_error(exc) from exc
    return RegionDistortion(
        session_id=session_id,
        region_id=region_id,
        distortion_degree=max(0.0, min(1.0, body.degree)),
    )


@router.post("/sessions/{session_id}/advance-turn", response_model=TurnResult)
def advance_turn(session_id: str, request: Request) -> TurnResult:
    try:
        return _svc(request, "game_master").advance_turn(session_id)
    except (LookupError, SessionClosedError) as exc:
        raise _session_error(exc) from exc


@router.get("/sessions/{session_id}/regions/{region_id}/knowledge", response_model=QueryResult)
def session_knowledge(session_id: str, region_id: str, request: Request) -> QueryResult:
    try:
        return _svc(request, "session_query").knowledge_for_region(session_id, region_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
