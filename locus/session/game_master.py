"""GameMasterService — per-turn session orchestrator (S2, FR-R2/R3/R4).

Drives one session's dynamic state a turn at a time: generate / regenerate
rumors, adjust support, set per-region distortion, and advance the turn
(re-evaluating promotion). Every action records exactly one TimelineEntry.
Canonical access (source collection via ConsensusEngine) is read-only (NFR-R2).
"""

from __future__ import annotations

from pydantic import Field

from ..consensus.engine import DEFAULT_PARAMS, ConsensusEngine, ConsensusParams
from ..models import LocusModel, Provenance, SourceKind
from ..query.loader import WorldLoader
from . import dynamics, promotion
from .event_suggester import EventSuggester
from .models import (
    DEFAULT_DISTORTION_DEGREE,
    EventCategory,
    EventLifecycle,
    EventStatus,
    GameSession,
    RegionDistortion,
    SessionEvent,
    SessionRumor,
    SessionStatus,
    TimelineEntry,
    TimelineKind,
    default_lifecycle,
)
from .repository import SessionRepository
from .rumor_generator import RumorGenerator

# Q1=A: chain degrees = region_distortion * these fractions (region degree = cap).
DEFAULT_CHAIN_FRACTIONS = [1 / 3, 2 / 3, 1.0]


class SessionClosedError(RuntimeError):
    """Raised when a write action targets a CLOSED session (BR-S2-9)."""


class TurnResult(LocusModel):
    """Summary of an advance_turn call."""

    session_id: str
    turn: int
    promoted_ids: list[str] = Field(default_factory=list)
    demoted_ids: list[str] = Field(default_factory=list)
    # Phase 2 (additive) — events applied / auto-resolved (one_shot) this turn
    applied_event_ids: list[str] = Field(default_factory=list)
    resolved_event_ids: list[str] = Field(default_factory=list)


class GameMasterService:
    def __init__(
        self,
        repo: SessionRepository,
        generator: RumorGenerator,
        loader: WorldLoader,
        params: ConsensusParams = DEFAULT_PARAMS,
        *,
        suggester: EventSuggester | None = None,
    ) -> None:
        self._repo = repo
        self._gen = generator
        self._loader = loader
        self._params = params
        self._suggester = suggester  # Phase 2: optional LLM event proposals (BR-P2-16)

    # -- reads ------------------------------------------------------------ #
    def list_rumors(self, session_id: str, region_id: str) -> list[SessionRumor]:
        """Read-only list of a region's session rumors (allowed on closed sessions)."""
        if self._repo.get_session(session_id) is None:
            raise LookupError(f"session not found: {session_id}")
        return self._repo.list_rumors(session_id, region_id)

    def list_events(self, session_id: str, *, status: str | None = None) -> list[SessionEvent]:
        """Read-only list of session events (allowed on closed sessions)."""
        if self._repo.get_session(session_id) is None:
            raise LookupError(f"session not found: {session_id}")
        return self._repo.list_events(session_id, status)

    def list_distortions(self, session_id: str) -> list[RegionDistortion]:
        """Read-only list of per-region distortion (allowed on closed sessions)."""
        if self._repo.get_session(session_id) is None:
            raise LookupError(f"session not found: {session_id}")
        return self._repo.list_region_distortions(session_id)

    # -- events (Phase 2: P1 manual lifecycle) ---------------------------- #
    def create_event(
        self,
        session_id: str,
        region_id: str,
        *,
        category: EventCategory,
        description: str = "",
        magnitude: float,
        lifecycle: EventLifecycle | None = None,
    ) -> SessionEvent:
        """Manually create an ACTIVE event (FR-P2.1). Validates the region (BR-P1-2)."""
        session = self._require_open(session_id)
        self._require_region(session.world_id, region_id)
        cat = EventCategory(category)
        event = SessionEvent(
            session_id=session_id,
            region_id=region_id,
            category=cat,
            description=description,
            magnitude=_clamp(magnitude),
            lifecycle=lifecycle or default_lifecycle(cat),
            status=EventStatus.ACTIVE,
            created_turn=session.turn,
            provenance=Provenance(source=SourceKind.SESSION_EVENT, generated_by="gm:event"),
        )
        saved = self._repo.create_event(event)
        self._timeline(
            session,
            TimelineKind.EVENT_CREATED,
            f"created {cat.value} event in {region_id}",
            {
                "event_id": saved.id,
                "region_id": region_id,
                "category": cat.value,
                "magnitude": saved.magnitude,
            },
        )
        return saved

    def resolve_event(self, session_id: str, event_id: str) -> SessionEvent:
        """Resolve an event (FR-P3.6). Restores its accumulated distortion (BR-P2-5)."""
        session = self._require_open(session_id)
        event = self._repo.get_event(session_id, event_id)
        if event is None:
            raise LookupError(f"event not found: {event_id}")
        if event.status == EventStatus.RESOLVED.value:  # idempotent (BR-P1-6)
            return event
        if event.contributions:  # symmetric restore (target + propagated neighbours)
            cur = {
                rd.region_id: rd.distortion_degree
                for rd in self._repo.list_region_distortions(session_id)
            }
            cur = dynamics.restore_contributions(cur, event.contributions)
            for rid in event.contributions:
                self._repo.set_region_distortion(session_id, rid, cur[rid])
        event.status = EventStatus.RESOLVED
        event.resolved_turn = session.turn
        saved = self._repo.update_event(event)
        self._timeline(
            session,
            TimelineKind.EVENT_RESOLVED,
            f"resolved event {event_id}",
            {"event_id": event_id, "restored": event.contributions},
        )
        return saved

    def discard_event(self, session_id: str, event_id: str) -> None:
        """Discard a SUGGESTED event (BR-P1-8). ACTIVE/RESOLVED cannot be discarded."""
        self._require_open(session_id)
        event = self._repo.get_event(session_id, event_id)
        if event is None:
            raise LookupError(f"event not found: {event_id}")
        if event.status != EventStatus.SUGGESTED.value:
            raise ValueError(f"only SUGGESTED events can be discarded: {event_id}")
        self._repo.delete_event(session_id, event_id)

    def suggest_events(self, session_id: str, *, n: int = 1) -> list[SessionEvent]:
        """LLM proposes up to ``n`` events, persisted as SUGGESTED (FR-P2.2, BR-P2-10).

        Graceful: no suggester or LLM failure -> []. Invalid-region drafts skipped.
        """
        session = self._require_open(session_id)
        if self._suggester is None:
            return []
        _kg, topo = self._loader.load(session.world_id)
        region_ids = {r.id for r in topo.regions}
        drafts = self._suggester.suggest(
            world_id=session.world_id,
            region_ids=list(region_ids),
            turn=session.turn,
            n=n,
        )
        out: list[SessionEvent] = []
        for d in drafts:
            if d.region_id not in region_ids:  # skip invalid region (BR-P2-10)
                continue
            cat = EventCategory(d.category)
            event = SessionEvent(
                session_id=session_id,
                region_id=d.region_id,
                category=cat,
                description=d.description,
                magnitude=_clamp(d.magnitude),
                lifecycle=default_lifecycle(cat),
                status=EventStatus.SUGGESTED,
                created_turn=session.turn,
                provenance=Provenance(source=SourceKind.SESSION_EVENT, generated_by="llm:event"),
            )
            saved = self._repo.create_event(event)
            out.append(saved)
            self._timeline(
                session,
                TimelineKind.EVENT_CREATED,
                f"suggested {cat.value} event in {d.region_id}",
                {"event_id": saved.id, "region_id": d.region_id, "suggested": True},
            )
        return out

    def approve_event(self, session_id: str, event_id: str) -> SessionEvent:
        """Approve a SUGGESTED event -> ACTIVE (FR-P2.3, CL2.1=A)."""
        session = self._require_open(session_id)
        event = self._repo.get_event(session_id, event_id)
        if event is None:
            raise LookupError(f"event not found: {event_id}")
        if event.status != EventStatus.SUGGESTED.value:
            raise ValueError(f"only SUGGESTED events can be approved: {event_id}")
        event.status = EventStatus.ACTIVE
        saved = self._repo.update_event(event)
        self._timeline(
            session,
            TimelineKind.EVENT_CREATED,
            f"approved event {event_id}",
            {"event_id": event_id, "approved": True},
        )
        return saved

    # -- actions ---------------------------------------------------------- #
    def generate_rumors(
        self, session_id: str, region_id: str, *, degrees: list[float] | None = None
    ) -> list[SessionRumor]:
        session = self._require_open(session_id)
        degrees = degrees or self._chain_degrees(session_id, region_id)
        rumors = self._generate_for_region(session, region_id, degrees)
        self._timeline(
            session,
            TimelineKind.GENERATE,
            f"generated {len(rumors)} rumors in {region_id}",
            {"region_id": region_id, "rumor_ids": [r.id for r in rumors]},
        )
        return rumors

    def regenerate_region(self, session_id: str, region_id: str) -> list[SessionRumor]:
        session = self._require_open(session_id)
        existing = self._repo.list_rumors(session_id, region_id)
        for r in existing:  # Q4=A: drop all (incl. promoted) then regenerate
            self._repo.delete_rumor(session_id, r.id)
        degrees = self._chain_degrees(session_id, region_id)
        rumors = self._generate_for_region(session, region_id, degrees)
        self._timeline(
            session,
            TimelineKind.REGENERATE,
            f"regenerated {region_id}",
            {
                "region_id": region_id,
                "deleted": [r.id for r in existing],
                "rumor_ids": [r.id for r in rumors],
            },
        )
        return rumors

    def adjust_support(self, session_id: str, rumor_id: str, support: float) -> SessionRumor:
        session = self._require_open(session_id)
        rumor = self._repo.get_rumor(session_id, rumor_id)
        if rumor is None:
            raise LookupError(f"rumor not found: {rumor_id}")
        rumor.support = _clamp(support)
        saved = self._repo.upsert_rumor(rumor)
        self._timeline(
            session,
            TimelineKind.ADJUST_SUPPORT,
            f"support of {rumor_id} -> {rumor.support:.2f}",
            {"rumor_id": rumor_id, "support": rumor.support},
        )
        return saved

    def set_region_distortion(self, session_id: str, region_id: str, degree: float) -> None:
        session = self._require_open(session_id)
        degree = _clamp(degree)
        self._repo.set_region_distortion(session_id, region_id, degree)
        self._timeline(
            session,
            TimelineKind.SET_DISTORTION,
            f"distortion of {region_id} -> {degree:.2f}",
            {"region_id": region_id, "degree": degree},
        )

    def advance_turn(
        self, session_id: str, *, promotion_threshold: float = promotion.DEFAULT_PROMOTION_THRESHOLD
    ) -> TurnResult:
        """Advance one turn (FR-P3.3): apply events -> update rumors -> evolve
        support -> re-evaluate promotion -> bump. Each change is timelined."""
        session = self._require_open(session_id)
        applied_ids, resolved_ids, influenced = self._apply_active_events(session)

        # (2) primary-region rumors: append at the new distortion, preserving
        #     existing rumors + support (FR-P4.1 / BR-P2-7). Neighbours: distortion only.
        for region_id in {self._repo.get_event(session_id, eid).region_id for eid in applied_ids}:
            self._generate_for_region(
                session, region_id, self._chain_degrees(session_id, region_id)
            )

        # (3) support auto-evolution (FR-P5.1 / BR-P2-8)
        rumors = self._repo.list_rumors(session_id)
        for r in dynamics.evolve_support(rumors, influenced):
            self._repo.upsert_rumor(r)

        # (4) promotion / demotion re-evaluation (Phase 1 reuse)
        res = promotion.evaluate(self._repo.list_rumors(session_id), promotion_threshold)
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
                "applied": applied_ids,
                "resolved": resolved_ids,
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
            applied_event_ids=applied_ids,
            resolved_event_ids=resolved_ids,
        )

    # -- internals -------------------------------------------------------- #
    def _apply_active_events(self, session: GameSession) -> tuple[list[str], list[str], set[str]]:
        """Apply all ACTIVE events to region distortion (step 1 of advance_turn).

        Returns (applied_ids, resolved_ids, influenced_region_ids). Canonical
        topology is read-only (NFR-P2). one_shot events auto-resolve (BR-P2-4);
        persistent ones accumulate contributions for later restore (BR-P2-3/5).
        """
        _kg, topo = self._loader.load(session.world_id)
        active = self._repo.list_events(session.id, EventStatus.ACTIVE.value)
        cur = {
            rd.region_id: rd.distortion_degree
            for rd in self._repo.list_region_distortions(session.id)
        }
        applied_ids: list[str] = []
        resolved_ids: list[str] = []
        influenced: set[str] = set()
        for ev in active:
            base = dynamics.distortion_delta(ev.magnitude)
            deltas = dynamics.propagate_delta(ev.region_id, base, topo.connections)
            cur = dynamics.apply_deltas(cur, deltas)
            ev.contributions = dynamics.merge_add(ev.contributions, deltas)
            influenced |= set(deltas)
            applied_ids.append(ev.id)
            if ev.lifecycle == EventLifecycle.ONE_SHOT.value:  # BR-P2-4: 1-shot, no restore
                ev.status = EventStatus.RESOLVED
                ev.resolved_turn = session.turn + 1
                resolved_ids.append(ev.id)
            self._repo.update_event(ev)
            self._timeline(
                session,
                TimelineKind.EVENT_APPLIED,
                f"applied event {ev.id}",
                {"event_id": ev.id, "region_id": ev.region_id, "deltas": deltas},
            )
        for rid, deg in cur.items():
            self._repo.set_region_distortion(session.id, rid, deg)
        return applied_ids, resolved_ids, influenced

    def _generate_for_region(
        self, session: GameSession, region_id: str, degrees: list[float]
    ) -> list[SessionRumor]:
        rumors: list[SessionRumor] = []
        for text, sid, kind, conf in self._collect_sources(session.world_id, region_id, session.id):
            chain = self._gen.generate_chain(
                source_text=text,
                source_id=sid,
                source_kind=kind,
                source_confidence=conf,
                region_id=region_id,
                session_id=session.id,
                degrees=degrees,
            )
            for r in chain:
                rumors.append(self._repo.upsert_rumor(r))
        return rumors

    def _collect_sources(
        self, world_id: str, region_id: str, session_id: str
    ) -> list[tuple[str, str, str, float]]:
        """Sources = region direct + propagated canonical knowledge + existing
        session rumors (Q2). (text, id, kind, confidence)."""
        kg, topo = self._loader.load(world_id)
        if region_id not in {r.id for r in topo.regions}:
            raise LookupError(f"region not found: {region_id}")
        view = ConsensusEngine(kg, topo, self._params).resolve(region_id)
        sources: list[tuple[str, str, str, float]] = []
        for kv in view.direct + view.propagated:  # Q2: direct + propagated
            sources.append((kv.statement, kv.knowledge_id, "knowledge", kv.confidence))
        for r in self._repo.list_rumors(session_id, region_id):  # existing rumors (chain)
            sources.append((r.statement, r.id, "rumor", r.confidence))
        return sources

    def _require_region(self, world_id: str, region_id: str) -> None:
        """Validate a region exists in the canonical topology (read-only; BR-P1-2)."""
        _kg, topo = self._loader.load(world_id)
        if region_id not in {r.id for r in topo.regions}:
            raise LookupError(f"region not found: {region_id}")

    def _chain_degrees(self, session_id: str, region_id: str) -> list[float]:
        d = self._repo.get_region_distortion(session_id, region_id)
        if d is None:
            d = DEFAULT_DISTORTION_DEGREE
        return [_clamp(f * d) for f in DEFAULT_CHAIN_FRACTIONS]

    def _set_promoted(self, session_id: str, rumor_id: str, promoted: bool) -> None:
        rumor = self._repo.get_rumor(session_id, rumor_id)
        if rumor is None:  # pragma: no cover - id came from list_rumors
            return
        rumor.promoted = promoted
        self._repo.upsert_rumor(rumor)

    def _timeline(
        self,
        session: GameSession,
        kind: TimelineKind,
        summary: str,
        payload: dict,
        *,
        turn: int | None = None,
    ) -> None:
        self._repo.append_timeline(
            TimelineEntry(
                session_id=session.id,
                turn=session.turn if turn is None else turn,
                kind=kind,
                summary=summary,
                payload=payload,
            )
        )

    def _require_open(self, session_id: str) -> GameSession:
        session = self._repo.get_session(session_id)
        if session is None:
            raise LookupError(f"session not found: {session_id}")
        if session.status == SessionStatus.CLOSED.value:
            raise SessionClosedError(f"session is closed: {session_id}")
        return session


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
