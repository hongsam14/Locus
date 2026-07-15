"""TurnAdvancer — the per-turn advance sequence (Phase 2, FR-P3.3).

Orchestrates one turn over the injected services: apply ACTIVE events to
distortion -> append rumors in affected regions -> auto-evolve support ->
re-evaluate promotion -> bump the turn. Each change records one TimelineEntry.
Distortion/propagation/support evolution are deterministic (LLM-independent).
"""

from __future__ import annotations

from pydantic import Field

from ..models import LocusModel
from ..query.loader import WorldLoader
from . import dynamics, promotion
from .base import SessionAppService
from .models import DEFAULT_DISTORTION_DEGREE, EventStatus, GameSession, TimelineKind
from .repository import SessionRepository
from .rumor_service import RumorService


class TurnResult(LocusModel):
    """Summary of an advance_turn call."""

    session_id: str
    turn: int
    promoted_ids: list[str] = Field(default_factory=list)
    demoted_ids: list[str] = Field(default_factory=list)
    # Phase 2 (additive) — events applied / auto-resolved (one_shot) this turn
    applied_event_ids: list[str] = Field(default_factory=list)
    resolved_event_ids: list[str] = Field(default_factory=list)


class _EventApplication(LocusModel):
    """Outcome of applying ACTIVE events for one turn (internal to advance_turn)."""

    applied_ids: list[str] = Field(default_factory=list)
    resolved_ids: list[str] = Field(default_factory=list)
    # primary target regions of applied events (where rumors are appended next)
    target_regions: set[str] = Field(default_factory=set)
    # every region whose distortion moved (drives support auto-evolution)
    influenced_regions: set[str] = Field(default_factory=set)


class TurnAdvancer(SessionAppService):
    """Advance a session one turn by composing the rumor / event / distortion steps."""

    def __init__(
        self,
        repo: SessionRepository,
        loader: WorldLoader,
        rumors: RumorService,
    ) -> None:
        super().__init__(repo)
        self._loader = loader
        self._rumors = rumors

    def advance_turn(
        self, session_id: str, *, promotion_threshold: float = promotion.DEFAULT_PROMOTION_THRESHOLD
    ) -> TurnResult:
        """Advance one turn (FR-P3.3): apply events -> update rumors -> evolve
        support -> re-evaluate promotion -> bump. Each change is timelined."""
        session = self._require_open(session_id)

        # (1) apply ACTIVE events to per-region distortion
        events = self._apply_active_events(session)

        # (2) primary-region rumors: append at the new distortion, preserving
        #     existing rumors + support (FR-P4.1 / BR-P2-7). Neighbours: distortion only.
        for region_id in events.target_regions:
            self._rumors.append_for_region(session, region_id)

        # (3) support auto-evolution (FR-P5.1 / BR-P2-8) — only when events acted
        #     this turn. A plain empty turn must not erode support (which would
        #     silently demote promoted rumors the GM never touched).
        rumors = self._repo.list_rumors(session_id)
        if events.influenced_regions:
            for r in dynamics.evolve_support(rumors, events.influenced_regions):
                self._repo.upsert_rumor(r)

        # (4) promotion / demotion re-evaluation — reuses the step-3 list (already
        #     current: evolve_support mutates in place)
        res = promotion.evaluate(rumors, promotion_threshold)
        for rid in res.promoted_ids:
            self._set_promoted(session_id, rid, True)
            self._timeline(session, TimelineKind.PROMOTE, f"promoted {rid}", {"rumor_id": rid})
        for rid in res.demoted_ids:
            self._set_promoted(session_id, rid, False)
            self._timeline(session, TimelineKind.DEMOTE, f"demoted {rid}", {"rumor_id": rid})

        # (5) bump turn + summary timeline
        new_turn = self._repo.bump_turn(session_id)
        self._timeline(
            session,
            TimelineKind.ADVANCE_TURN,
            f"advanced to turn {new_turn}",
            {
                "applied": events.applied_ids,
                "resolved": events.resolved_ids,
                "promoted": res.promoted_ids,
                "demoted": res.demoted_ids,
            },
            turn=new_turn,
        )
        return TurnResult(
            session_id=session_id,
            turn=new_turn,
            promoted_ids=res.promoted_ids,
            demoted_ids=res.demoted_ids,
            applied_event_ids=events.applied_ids,
            resolved_event_ids=events.resolved_ids,
        )

    # -- internals -----------------------------------------------------------
    def _apply_active_events(self, session: GameSession) -> _EventApplication:
        """Apply all ACTIVE events to region distortion (step 1 of advance_turn).

        Canonical topology is read-only (NFR-P2). one_shot events auto-resolve
        (BR-P2-4); persistent ones accumulate contributions for later restore
        (BR-P2-3/5). Returns the ids/regions the later steps need.
        """
        _kg, topo = self._loader.load(session.world_id)
        active = self._repo.list_events(session.id, EventStatus.ACTIVE.value)
        cur = {
            rd.region_id: rd.distortion_degree
            for rd in self._repo.list_region_distortions(session.id)
        }
        out = _EventApplication()
        for ev in active:
            base = dynamics.distortion_delta(ev.magnitude)
            deltas = dynamics.propagate_delta(ev.region_id, base, topo.connections)
            updated = dynamics.apply_deltas(cur, deltas)
            # Accumulate the *effective* (post-clamp) change, not the raw delta, so
            # resolve restores exactly what was applied even when distortion
            # saturated at 1.0 — otherwise the restore over-subtracts and drives
            # the region below its pre-event baseline.
            effective = {
                rid: updated[rid] - cur.get(rid, DEFAULT_DISTORTION_DEGREE) for rid in deltas
            }
            cur = updated
            ev.accumulate(effective)
            out.applied_ids.append(ev.id)
            out.target_regions.add(ev.region_id)
            out.influenced_regions |= set(deltas)
            if ev.is_one_shot():  # BR-P2-4: 1-shot, no restore
                ev.resolve(session.turn + 1)
                out.resolved_ids.append(ev.id)
            self._repo.update_event(ev)
            self._timeline(
                session,
                TimelineKind.EVENT_APPLIED,
                f"applied event {ev.id}",
                {"event_id": ev.id, "region_id": ev.region_id, "deltas": effective},
            )
        for rid, deg in cur.items():
            self._repo.set_region_distortion(session.id, rid, deg)
        return out

    def _set_promoted(self, session_id: str, rumor_id: str, promoted: bool) -> None:
        rumor = self._repo.get_rumor(session_id, rumor_id)
        if rumor is None:  # pragma: no cover - id came from list_rumors
            return
        rumor.promoted = promoted
        self._repo.upsert_rumor(rumor)
