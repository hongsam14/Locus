"""play router — sessions, the player screen and player actions (U4). No auth (MVP).

Contracts (U4 code plan, 유닛 컨텍스트): ``POST /worlds/{w}/sessions`` without a
body keeps the pre-U4 GM session (200 ``GameSession``); with a ``PlayerCreate``
body it starts a player-mode session (201 ``SessionStartOut``). ``POST
/sessions/{s}/act`` answers 202 with the ``TurnRun`` and the turns run in the
background; ``GET /sessions/{s}/turn-runs/{id}`` is the poll. NPC dialogue lands
here in U5.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse

from api.deps import display_lang, get_localization, get_play
from api.errors import PLAY_ERRORS, http_error
from api.schemas import (
    ConversationOut,
    NpcReplyOut,
    NpcSummaryOut,
    QueryResultOut,
    RegionViewOut,
    SayIn,
    SessionStartOut,
    localize_query_result,
    localize_region_view,
)
from locus.localization.wiring import LocalizationContainer
from locus.play.models import (
    GameSession,
    Player,
    PlayerAction,
    PlayerCreate,
    TimelineEntry,
    TurnRun,
)
from locus.play.wiring import PlayContainer

router = APIRouter(prefix="/api/play", tags=["play"])


@router.post(
    "/worlds/{world_id}/sessions",
    response_model=None,
    responses={
        200: {"model": GameSession, "description": "GM session without a player (no body)"},
        201: {"model": SessionStartOut, "description": "Player-mode session (body given)"},
    },
)
def start_session(
    world_id: str,
    body: PlayerCreate | None = Body(default=None),
    p: PlayContainer = Depends(get_play),
) -> Any:
    try:
        if body is None:  # pre-U4 contract: GM session, 200 GameSession
            return p.sessions.start_session(world_id)
        session, player = p.sessions.start(world_id, body)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc
    out = SessionStartOut(session=session, player=player)
    return JSONResponse(status_code=201, content=out.model_dump(mode="json"))


@router.get("/worlds/{world_id}/sessions", response_model=list[GameSession])
def list_sessions(world_id: str, p: PlayContainer = Depends(get_play)) -> list[GameSession]:
    return p.sessions.list_sessions(world_id)


@router.get("/sessions/{session_id}", response_model=GameSession)
def get_session(session_id: str, p: PlayContainer = Depends(get_play)) -> GameSession:
    try:
        return p.sessions.get_session(session_id)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc


@router.post("/sessions/{session_id}/close", response_model=GameSession)
def close_session(session_id: str, p: PlayContainer = Depends(get_play)) -> GameSession:
    try:
        return p.sessions.close_session(session_id)  # 409 while a turn run is in progress
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc


# --- player screen (U4) --------------------------------------------------------- #
@router.get("/sessions/{session_id}/player", response_model=Player)
def get_player(session_id: str, p: PlayContainer = Depends(get_play)) -> Player:
    try:
        return p.play.player(session_id)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc


@router.get("/sessions/{session_id}/region", response_model=RegionViewOut)
def current_region(
    session_id: str,
    lang: str = Depends(display_lang),
    p: PlayContainer = Depends(get_play),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> RegionViewOut:
    """The player's current region in one payload (FR-C5): name, path, NPCs, what is
    known / heard / rumoured, and the move options. Read-only."""
    try:
        session = p.sessions.get_session(session_id)
        view = p.play.current_region(session_id)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc
    return localize_region_view(
        view, loc, world_id=session.world_id, session_id=session_id, lang=lang
    )


@router.post("/sessions/{session_id}/act", response_model=TurnRun, status_code=202)
def act(
    session_id: str,
    action: PlayerAction = Body(...),
    lang: str = Depends(display_lang),
    p: PlayContainer = Depends(get_play),
) -> TurnRun:
    """Move / wait / end a talk / declare (FR-C3, FR-C9). Validates, applies the
    immediate state and answers 202 with the running ``TurnRun``; poll
    ``turn-runs/{id}`` (Q4=A). ``lang`` is the language a declaration is narrated in."""
    try:
        return p.play.act(session_id, action, lang=lang)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc


@router.get("/sessions/{session_id}/turn-runs", response_model=list[TurnRun])
def list_turn_runs(
    session_id: str, status: str | None = None, p: PlayContainer = Depends(get_play)
) -> list[TurnRun]:
    try:
        return p.play.list_runs(session_id, status)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc


@router.get("/sessions/{session_id}/turn-runs/{run_id}", response_model=TurnRun)
def get_turn_run(session_id: str, run_id: str, p: PlayContainer = Depends(get_play)) -> TurnRun:
    try:
        return p.play.turn_run(session_id, run_id)  # 404 for another session's run (R-06)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc


@router.get("/sessions/{session_id}/log", response_model=list[TimelineEntry])
def play_log(session_id: str, p: PlayContainer = Depends(get_play)) -> list[TimelineEntry]:
    """The session timeline (U4 basic; the player-perspective filter is U7)."""
    try:
        return p.play.log(session_id)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc


@router.get("/sessions/{session_id}/regions/{region_id}/knowledge", response_model=QueryResultOut)
def session_knowledge(
    session_id: str,
    region_id: str,
    lang: str = Depends(display_lang),
    p: PlayContainer = Depends(get_play),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> QueryResultOut:
    """What this region's inhabitants know right now: canonical + active session rumors (FR-F5)."""
    try:
        result = p.region_knowledge.knowledge_for_region(session_id, region_id)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc
    return localize_query_result(result, loc, session_id=session_id, lang=lang)


# --- NPC dialogue (U5) ------------------------------------------------------------ #
@router.get("/sessions/{session_id}/npcs", response_model=list[NpcSummaryOut])
def list_npcs(session_id: str, p: PlayContainer = Depends(get_play)) -> list[NpcSummaryOut]:
    """The people of the player's current region (US-4.1)."""
    try:
        pairs = p.dialogue.npcs_here(session_id)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc
    return [
        NpcSummaryOut(
            npc=npc,
            has_conversation=conv is not None,
            message_count=len(conv.messages) if conv else 0,
        )
        for npc, conv in pairs
    ]


@router.post("/sessions/{session_id}/npcs/{npc_id}/start", response_model=ConversationOut)
def start_dialogue(
    session_id: str, npc_id: str, p: PlayContainer = Depends(get_play)
) -> ConversationOut:
    """Open or reopen the conversation (no LLM — works without a provider)."""
    try:
        return p.dialogue.start(session_id, npc_id)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc


@router.post("/sessions/{session_id}/npcs/{npc_id}/say", response_model=NpcReplyOut)
def say(
    session_id: str,
    npc_id: str,
    body: SayIn,
    lang: str = Depends(display_lang),
    p: PlayContainer = Depends(get_play),
) -> NpcReplyOut:
    """One line to an NPC; one LLM call; the answer in the display language (FR-C4/G3).
    400 bad text / wrong region, 404 unknown NPC, 409 closed, 503 without a provider."""
    try:
        return p.dialogue.say(session_id, npc_id, body.text, lang=lang)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc


@router.get("/sessions/{session_id}/npcs/{npc_id}/history", response_model=ConversationOut)
def dialogue_history(
    session_id: str, npc_id: str, p: PlayContainer = Depends(get_play)
) -> ConversationOut:
    try:
        return p.dialogue.history(session_id, npc_id)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc
