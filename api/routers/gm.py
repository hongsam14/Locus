"""gm router — GameMaster tools: rumors, distortion, events, manual turn, timeline. No auth (MVP)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TypeVar

from fastapi import APIRouter, Depends

from api.deps import display_lang, get_localization, get_play
from api.errors import PLAY_ERRORS, http_error
from api.schemas import (
    DeedAppraisalOut,
    DeedOut,
    DeedViewOut,
    DistortionUpdate,
    EventCreate,
    EventOut,
    RumorOut,
    SupportUpdate,
    enrichment_for,
    localize,
    purge_translations,
)
from locus.localization.wiring import LocalizationContainer
from locus.play.errors import TurnInProgressError
from locus.play.models import (
    RegionDistortion,
    SessionEvent,
    SessionRumor,
    TimelineEntry,
    VoidResult,
)
from locus.play.turn.advancer import TurnResult
from locus.play.wiring import PlayContainer
from locus.shared.models.util import clamp01

router = APIRouter(prefix="/api/gm", tags=["gm"])

T = TypeVar("T")


def _idle(session_id: str, p: PlayContainer = Depends(get_play)) -> Iterator[None]:
    """Hold the session for the whole GM write (U4, BR-U4-13 / FD R-06).

    A turn run and a GM write may not overlap. This is a *lease*, not a check: the
    guard is held until the response is produced, because a GM write spends seconds in
    LLM calls and a turn starting in that gap deleted a rumor the turn had just
    promoted (code review U4-2 #7). A busy session answers 409 at once; reads are
    never blocked.
    """
    try:
        with p.guard.hold(session_id):
            yield
    except TurnInProgressError as exc:
        raise http_error(exc) from exc


def _rumors_out(
    loc: LocalizationContainer | None,
    session_id: str,
    rumors: list[SessionRumor],
    *,
    enrich: bool = True,
    lang: str | None = None,
) -> list[RumorOut]:
    """Read paths enrich from the translation cache (and warm misses); write paths
    return ``statement_ko=None`` without touching the translator (X1 Q2=A, review U1 #5).
    ``lang=None`` is the server default; write paths never reach the translator."""
    enrichment = (
        enrichment_for(
            loc, rumors, kind="rumor", fields=["statement"], session_id=session_id, lang=lang
        )
        if enrich
        else {}
    )
    return localize(rumors, RumorOut, enrichment, [("statement", "statement_ko")])


def _events_out(
    loc: LocalizationContainer | None,
    session_id: str,
    events: list[SessionEvent],
    *,
    enrich: bool = True,
    lang: str | None = None,
) -> list[EventOut]:
    enrichment = (
        enrichment_for(
            loc, events, kind="event", fields=["description"], session_id=session_id, lang=lang
        )
        if enrich
        else {}
    )
    return localize(events, EventOut, enrichment, [("description", "description_ko")])


# --- timeline ---------------------------------------------------------------- #
@router.get("/sessions/{session_id}/timeline", response_model=list[TimelineEntry])
def get_timeline(session_id: str, p: PlayContainer = Depends(get_play)) -> list[TimelineEntry]:
    try:
        return p.sessions.get_timeline(session_id)
    except LookupError as exc:
        raise http_error(exc) from exc


# --- rumors ------------------------------------------------------------------ #
@router.get("/sessions/{session_id}/regions/{region_id}/rumors", response_model=list[RumorOut])
def list_rumors(
    session_id: str,
    region_id: str,
    lang: str = Depends(display_lang),
    p: PlayContainer = Depends(get_play),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> list[RumorOut]:
    try:
        rumors = p.rumors.list_rumors(session_id, region_id)
    except LookupError as exc:
        raise http_error(exc) from exc
    return _rumors_out(loc, session_id, rumors, lang=lang)


@router.post(
    "/sessions/{session_id}/regions/{region_id}/rumors",
    response_model=list[RumorOut],
    dependencies=[Depends(_idle)],
)
def generate_rumors(
    session_id: str,
    region_id: str,
    p: PlayContainer = Depends(get_play),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> list[RumorOut]:
    try:
        rumors = p.rumors.generate_rumors(session_id, region_id)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc
    return _rumors_out(loc, session_id, rumors, enrich=False)


@router.post(
    "/sessions/{session_id}/regions/{region_id}/rumors/regen",
    response_model=list[RumorOut],
    dependencies=[Depends(_idle)],
)
def regenerate_region(
    session_id: str,
    region_id: str,
    p: PlayContainer = Depends(get_play),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> list[RumorOut]:
    try:
        result = p.rumors.regenerate_region(session_id, region_id)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc
    # Q4=A: the replaced rumors' translations go with them. The two skip paths delete
    # nothing, so `deleted_ids` is empty and nothing is purged (BR-U5-23).
    purge_translations(loc, kind="rumor", ids=result.deleted_ids)
    return _rumors_out(loc, session_id, result.rumors, enrich=False)


@router.put(
    "/sessions/{session_id}/rumors/{rumor_id}/support",
    response_model=RumorOut,
    dependencies=[Depends(_idle)],
)
def adjust_support(
    session_id: str,
    rumor_id: str,
    body: SupportUpdate,
    p: PlayContainer = Depends(get_play),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> RumorOut:
    try:
        rumor = p.rumors.adjust_support(session_id, rumor_id, body.support)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc
    return _rumors_out(loc, session_id, [rumor], enrich=False)[0]


# --- distortion --------------------------------------------------------------- #
@router.put(
    "/sessions/{session_id}/regions/{region_id}/distortion",
    response_model=RegionDistortion,
    dependencies=[Depends(_idle)],
)
def set_distortion(
    session_id: str,
    region_id: str,
    body: DistortionUpdate,
    p: PlayContainer = Depends(get_play),
) -> RegionDistortion:
    try:
        p.distortions.set_region_distortion(session_id, region_id, body.degree)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc
    stored = p.repo.get_region_distortion(session_id, region_id)
    return RegionDistortion(
        session_id=session_id,
        region_id=region_id,
        distortion_degree=stored if stored is not None else clamp01(body.degree),
    )


@router.get("/sessions/{session_id}/distortions", response_model=list[RegionDistortion])
def list_distortions(
    session_id: str, p: PlayContainer = Depends(get_play)
) -> list[RegionDistortion]:
    try:
        return p.distortions.list_distortions(session_id)
    except LookupError as exc:
        raise http_error(exc) from exc


# --- turn --------------------------------------------------------------------- #
@router.post("/sessions/{session_id}/advance", response_model=TurnResult)
def advance(session_id: str, p: PlayContainer = Depends(get_play)) -> TurnResult:
    """Manual GM turn: the same engine the player's actions drive (U4, BR-U4-16);
    runs without an LLM (rumor drafts skipped). 409 while a run is in progress."""
    try:
        return p.turns.advance(session_id).turns[-1]
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc


# --- events -------------------------------------------------------------------- #
@router.get("/sessions/{session_id}/events", response_model=list[EventOut])
def list_events(
    session_id: str,
    status: str | None = None,
    lang: str = Depends(display_lang),
    p: PlayContainer = Depends(get_play),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> list[EventOut]:
    try:
        events = p.events.list_events(session_id, status=status)
    except LookupError as exc:
        raise http_error(exc) from exc
    return _events_out(loc, session_id, events, lang=lang)


@router.post(
    "/sessions/{session_id}/events", response_model=EventOut, dependencies=[Depends(_idle)]
)
def create_event(
    session_id: str,
    body: EventCreate,
    p: PlayContainer = Depends(get_play),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> EventOut:
    try:
        event = p.events.create_event(
            session_id,
            body.region_id,
            category=body.category,
            description=body.description,
            magnitude=body.magnitude,
            lifecycle=body.lifecycle,
        )
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc
    return _events_out(loc, session_id, [event], enrich=False)[0]


@router.post(
    "/sessions/{session_id}/events/suggest",
    response_model=list[EventOut],
    dependencies=[Depends(_idle)],
)
def suggest_events(
    session_id: str,
    n: int = 1,
    p: PlayContainer = Depends(get_play),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> list[EventOut]:
    try:
        events = p.events.suggest_events(session_id, n=n)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc
    return _events_out(loc, session_id, events, enrich=False)


@router.post(
    "/sessions/{session_id}/events/{event_id}/approve",
    response_model=EventOut,
    dependencies=[Depends(_idle)],
)
def approve_event(
    session_id: str,
    event_id: str,
    p: PlayContainer = Depends(get_play),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> EventOut:
    try:
        event = p.events.approve_event(session_id, event_id)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc
    return _events_out(loc, session_id, [event], enrich=False)[0]


@router.post(
    "/sessions/{session_id}/events/{event_id}/resolve",
    response_model=EventOut,
    dependencies=[Depends(_idle)],
)
def resolve_event(
    session_id: str,
    event_id: str,
    p: PlayContainer = Depends(get_play),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> EventOut:
    try:
        event = p.events.resolve_event(session_id, event_id)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc
    return _events_out(loc, session_id, [event], enrich=False)[0]


@router.delete(
    "/sessions/{session_id}/events/{event_id}", status_code=204, dependencies=[Depends(_idle)]
)
def discard_event(session_id: str, event_id: str, p: PlayContainer = Depends(get_play)) -> None:
    try:
        p.events.discard_event(session_id, event_id)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc


# --- U6 deeds (BLM §8; BR-U6-27/28/33) ---------------------------------------- #
@router.get("/sessions/{session_id}/deeds", response_model=list[DeedViewOut])
def list_deeds(
    session_id: str,
    lang: str = Depends(display_lang),
    p: PlayContainer = Depends(get_play),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> list[DeedViewOut]:
    """Every deed with its appraisals and rumors, newest first (US-5.6)."""
    try:
        views = p.deeds.views(session_id)
        regions, npcs = p.deeds.names(session_id)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc
    deeds = [v.deed for v in views]
    appraisals = [a for v in views for a in v.appraisals if a.retelling]
    deed_tr = enrichment_for(
        loc, deeds, kind="deed", fields=["text"], session_id=session_id, lang=lang
    )
    appraisal_tr = enrichment_for(
        loc,
        appraisals,
        kind="deed_appraisal",
        fields=["retelling"],
        session_id=session_id,
        lang=lang,
    )
    rumors_out = {
        r.id: r
        for r in _rumors_out(loc, session_id, [r for v in views for r in v.rumors], lang=lang)
    }
    out: list[DeedViewOut] = []
    for v in views:
        deed = DeedOut(
            **v.deed.model_dump(),
            text_ko=deed_tr.get(v.deed.id, {}).get("text"),
            region_name=regions.get(v.deed.region_id, v.deed.region_id),
            witness_names=[npcs.get(n, n) for n in v.deed.witnessed_npc_ids],
        )
        judged = [
            DeedAppraisalOut(
                **a.model_dump(),
                retelling_ko=appraisal_tr.get(a.id, {}).get("retelling"),
                npc_name=npcs.get(a.npc_id, a.npc_id),
            )
            for a in v.appraisals
        ]
        out.append(
            DeedViewOut(
                deed=deed,
                appraisals=judged,
                rumors=[rumors_out[r.id] for r in v.rumors],
                reached_region_ids=v.reached_region_ids,
                reached_region_names=[regions.get(r, r) for r in v.reached_region_ids],
            )
        )
    return out


@router.post(
    "/sessions/{session_id}/deeds/{deed_id}/void",
    response_model=VoidResult,
    dependencies=[Depends(_idle)],  # the GM write lease, held to the commit (BR-U6-28)
)
def void_deed(session_id: str, deed_id: str, p: PlayContainer = Depends(get_play)) -> VoidResult:
    """Undo a deed and every rumor it produced (US-5.6). 404 / 409, idempotent."""
    try:
        return p.deeds.void(session_id, deed_id)
    except PLAY_ERRORS as exc:
        raise http_error(exc) from exc
