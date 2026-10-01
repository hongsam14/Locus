"""EventService — SessionEvent manual lifecycle (Phase 2 / P1+P2).

Owns the operator-facing event lifecycle: create an ACTIVE event, resolve it
(restoring its accumulated distortion), discard a proposal, and the LLM
suggest -> approve gate. The per-turn *application* of active events to
distortion lives in TurnAdvancer; this service is the CRUD/lifecycle boundary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from locus.knowledge.cache import SnapshotSource
from locus.play.base import SessionAppService, require_region
from locus.play.errors import LlmUnavailableError
from locus.play.event import dynamics
from locus.play.event.suggester import EventSuggester
from locus.play.models import (
    EventCategory,
    EventLifecycle,
    EventStatus,
    GameSession,
    SessionEvent,
    TimelineKind,
    default_lifecycle,
)
from locus.play.ports import PlayRepository
from locus.shared.models import Provenance, SourceKind
from locus.shared.models.util import clamp01

if TYPE_CHECKING:  # wired by assemble_play
    from locus.play.deeds.service import DeedService


class EventService(SessionAppService):
    """Create / resolve / discard events and run the suggest->approve gate."""

    def __init__(
        self,
        repo: PlayRepository,
        snapshots: SnapshotSource,
        *,
        suggester: EventSuggester | None = None,
        deeds: DeedService | None = None,
    ) -> None:
        super().__init__(repo)
        self._snapshots = snapshots
        self._deeds = deeds  # U6: recent deeds feed the suggestion context (BR-U6-31)
        self._suggester = suggester  # optional LLM event proposals (BR-P2-16)

    @property
    def llm_available(self) -> bool:
        return self._suggester is not None

    # -- reads ---------------------------------------------------------------
    def list_events(self, session_id: str, *, status: str | None = None) -> list[SessionEvent]:
        """Read-only list of session events (allowed on closed sessions)."""
        self._require_session(session_id)
        return self._repo.list_events(session_id, status)

    # -- manual lifecycle ----------------------------------------------------
    def create_event(
        self,
        session_id: str,
        region_id: str,
        *,
        category: EventCategory,
        magnitude: float,
        description: str = "",
        lifecycle: EventLifecycle | None = None,
    ) -> SessionEvent:
        """Manually create an ACTIVE event (FR-P2.1). Validates the region (BR-P1-2)."""
        session = self._require_open(session_id)
        require_region(self._snapshots, session.world_id, region_id)
        cat = EventCategory(category)
        event = SessionEvent(
            session_id=session_id,
            region_id=region_id,
            category=cat,
            description=description,
            magnitude=clamp01(magnitude),
            lifecycle=lifecycle or default_lifecycle(cat),
            status=EventStatus.ACTIVE,
            created_turn=session.turn,
            provenance=Provenance(source=SourceKind.SIMULATION, generated_by="gm:event"),
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
        event = self._require_event(session_id, event_id)
        if event.is_resolved():  # idempotent (BR-P1-6)
            return event
        # Restore, status and timeline in ONE transaction: a failure part-way used to
        # leave some regions restored while the event stayed ACTIVE, so the next turn
        # accumulated a second contribution and the symmetric restore was permanently
        # broken (code review U4 #4). Deterministic body, no LLM — BR-U4-14 allows it.
        restored = dict(event.contributions)
        with self._repo.uow() as u:
            if restored:  # symmetric restore (target + propagated neighbours)
                cur = {
                    rd.region_id: rd.distortion_degree
                    for rd in u.distortions.list_region_distortions(session_id)
                }
                cur = dynamics.restore_contributions(cur, restored)
                for rid in restored:
                    u.distortions.set_region_distortion(session_id, rid, cur[rid])
            event.resolve(session.turn)
            saved = u.events.update_event(event)
            u.timeline.append_timeline(
                self._entry(
                    session,
                    TimelineKind.EVENT_RESOLVED,
                    f"resolved event {event_id}",
                    {"event_id": event_id, "restored": restored},
                )
            )
        return saved

    def discard_event(self, session_id: str, event_id: str) -> None:
        """Discard a SUGGESTED event (BR-P1-8). ACTIVE/RESOLVED cannot be discarded."""
        self._require_open(session_id)
        event = self._require_event(session_id, event_id)
        if not event.is_suggested():
            raise ValueError(f"only SUGGESTED events can be discarded: {event_id}")
        self._repo.delete_event(session_id, event_id)

    # -- suggest -> approve gate --------------------------------------------
    def suggest_events(self, session_id: str, *, n: int = 1) -> list[SessionEvent]:
        """LLM proposes up to ``n`` events, persisted as SUGGESTED (FR-P2.2, BR-P2-10).

        Needs a provider (503 without one); an LLM failure is graceful -> [].
        Invalid-region drafts are skipped.
        """
        if self._suggester is None:
            raise LlmUnavailableError("event suggestion needs an LLM provider (set OPENAI_API_KEY)")
        session = self._require_open(session_id)
        region_ids = set(self._snapshots.get(session.world_id).regions_by_id)
        drafts = self._suggester.suggest(
            world_id=session.world_id,
            region_ids=list(region_ids),
            turn=session.turn,
            n=n,
            context=self._deed_context(session),
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
                magnitude=clamp01(d.magnitude),
                lifecycle=default_lifecycle(cat),
                status=EventStatus.SUGGESTED,
                created_turn=session.turn,
                provenance=Provenance(source=SourceKind.SIMULATION, generated_by="llm:event"),
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
        event = self._require_event(session_id, event_id)
        if not event.is_suggested():
            raise ValueError(f"only SUGGESTED events can be approved: {event_id}")
        event.approve()
        saved = self._repo.update_event(event)
        self._timeline(
            session,
            TimelineKind.EVENT_CREATED,
            f"approved event {event_id}",
            {"event_id": event_id, "approved": True},
        )
        return saved

    # -- internals -----------------------------------------------------------
    def _require_event(self, session_id: str, event_id: str) -> SessionEvent:
        event = self._repo.get_event(session_id, event_id)
        if event is None:
            raise LookupError(f"event not found: {event_id}")
        return event

    def _deed_context(self, session: GameSession) -> str:
        """Recent deeds for the suggestion prompt (U6 BR-U6-31; FR-D2 보강): what the
        traveler did lately can give rise to events. Voided deeds are left out."""
        if self._deeds is None:
            return ""
        names = {r.id: r.name for r in self._snapshots.get(session.world_id).topo.regions}
        lines = []
        for deed, appraisals in self._deeds.recent(session.id, 5):
            line = f"- [{names.get(deed.region_id, deed.region_id)}] {deed.text}"
            told = next((a.retelling for a in appraisals if a.noteworthy and a.retelling), None)
            if told:
                line += f" (retold: {told})"
            lines.append(line)
        return ("Recent deeds of the traveler:\n" + "\n".join(lines)) if lines else ""
