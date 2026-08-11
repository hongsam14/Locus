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
from . import dynamics, promotion, rumor_dynamics
from .base import SessionAppService
from .models import DEFAULT_DISTORTION_DEGREE, EventStatus, GameSession, TimelineKind
from .repository import SessionRepository
from .rumor_dynamics import DEFAULT_RUMOR_DYNAMICS, RumorDynamicsParams
from .rumor_feedback_service import RumorFeedbackService
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
    # U-H1 (additive) — rumors pruned + regions moved by rumor feedback this turn
    pruned_rumor_ids: list[str] = Field(default_factory=list)
    feedback_regions: list[str] = Field(default_factory=list)


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
        feedback: RumorFeedbackService,
        params: RumorDynamicsParams = DEFAULT_RUMOR_DYNAMICS,
    ) -> None:
        super().__init__(repo)
        self._loader = loader
        self._rumors = rumors
        self._feedback = feedback
        self._params = params

    def advance_turn(
        self, session_id: str, *, promotion_threshold: float = promotion.DEFAULT_PROMOTION_THRESHOLD
    ) -> TurnResult:
        """Advance one turn (FR-P3.3 + U-H1): apply events -> append rumors
        (support-gated) -> rumor→region feedback -> reinforce/decay support ->
        prune -> re-evaluate promotion -> batch-persist -> bump. Each change is
        timelined. Step order = feedback → decay → prune (BR-H1-12)."""
        session = self._require_open(session_id)

        # (1) apply ACTIVE events to per-region distortion
        events = self._apply_active_events(session)

        # (2) primary-region rumors: append at the new distortion, preserving
        #     existing rumors + support (FR-P4.1 / BR-P2-7). Support-gated so weak
        #     rumors do not spawn new ones (FR-H2 / BR-H1-7).
        for region_id in events.target_regions:
            self._rumors.append_for_region(
                session, region_id, min_source_support=self._params.min_source_support
            )

        # (3) rumor→region distortion feedback (FR-H3 / BR-H1-9/10). Runs before
        #     decay so strong rumors reinforce their own regions this turn.
        rumors = self._repo.list_rumors(session_id)  # ACTIVE only (BR-H1-6/11)
        feedback_deltas = self._feedback.apply_feedback(session, rumors)
        reinforced = events.influenced_regions | set(feedback_deltas)  # BR-H1-2

        # (4) support evolution: event reinforcement first (Phase 2 gain, decay=0
        #     so it does not double-decay), then rumor_dynamics owns all decay of
        #     unreinforced rumors every turn (FR-H1 / BR-H1-1/2/3/20). Decay is the
        #     survival lever; promoted + reinforced (event ∪ feedback) rumors exempt.
        if events.influenced_regions:
            dynamics.evolve_support(rumors, events.influenced_regions, decay=0.0)
        rumor_dynamics.decay_support(rumors, reinforced, decay=self._params.support_decay)

        # (5) prune below the floor (soft-flag), promoted rumors exempt (FR-H1 /
        #     BR-H1-4/5; Q7=A). Survivors feed promotion re-evaluation.
        survivors, prunable = rumor_dynamics.partition_prunable(
            rumors, floor=self._params.prune_floor
        )
        for r in prunable:
            r.active = False
            self._timeline(session, TimelineKind.PRUNE, f"pruned {r.id}", {"rumor_id": r.id})

        # (6) promotion / demotion re-evaluation over surviving rumors
        res = promotion.evaluate(survivors, promotion_threshold)
        promoted = set(res.promoted_ids)
        demoted = set(res.demoted_ids)
        for r in survivors:
            if r.id in promoted:
                r.promoted = True
                self._timeline(
                    session, TimelineKind.PROMOTE, f"promoted {r.id}", {"rumor_id": r.id}
                )
            elif r.id in demoted:
                r.promoted = False
                self._timeline(session, TimelineKind.DEMOTE, f"demoted {r.id}", {"rumor_id": r.id})

        # (7) batch-persist all support/prune/promotion changes in one write (FR-H5 /
        #     BR-H1-13)
        self._repo.upsert_rumors(rumors)

        # (8) bump turn + summary timeline
        new_turn = self._repo.bump_turn(session_id)
        pruned_ids = [r.id for r in prunable]
        feedback_regions = sorted(feedback_deltas)
        self._timeline(
            session,
            TimelineKind.ADVANCE_TURN,
            f"advanced to turn {new_turn}",
            {
                "applied": events.applied_ids,
                "resolved": events.resolved_ids,
                "promoted": res.promoted_ids,
                "demoted": res.demoted_ids,
                "pruned": pruned_ids,
                "feedback_regions": feedback_regions,
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
            pruned_rumor_ids=pruned_ids,
            feedback_regions=feedback_regions,
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
