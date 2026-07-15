"""EventService — SessionEvent manual lifecycle (Phase 2 / P1+P2).

Owns the operator-facing event lifecycle: create an ACTIVE event, resolve it
(restoring its accumulated distortion), discard a proposal, and the LLM
suggest -> approve gate. The per-turn *application* of active events to
distortion lives in TurnAdvancer; this service is the CRUD/lifecycle boundary.
"""

from __future__ import annotations

from ..models import Provenance, SourceKind
from ..query.loader import WorldLoader
from . import dynamics
from .base import SessionAppService, clamp, require_region
from .event_suggester import EventSuggester
from .models import (
    EventCategory,
    EventLifecycle,
    EventStatus,
    SessionEvent,
    TimelineKind,
    default_lifecycle,
)
from .repository import SessionRepository


class EventService(SessionAppService):
    """Create / resolve / discard events and run the suggest->approve gate."""

    def __init__(
        self,
        repo: SessionRepository,
        loader: WorldLoader,
        *,
        suggester: EventSuggester | None = None,
    ) -> None:
        super().__init__(repo)
        self._loader = loader
        self._suggester = suggester  # optional LLM event proposals (BR-P2-16)

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
        require_region(self._loader, session.world_id, region_id)
        cat = EventCategory(category)
        event = SessionEvent(
            session_id=session_id,
            region_id=region_id,
            category=cat,
            description=description,
            magnitude=clamp(magnitude),
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
        event = self._require_event(session_id, event_id)
        if event.is_resolved():  # idempotent (BR-P1-6)
            return event
        if event.contributions:  # symmetric restore (target + propagated neighbours)
            cur = {
                rd.region_id: rd.distortion_degree
                for rd in self._repo.list_region_distortions(session_id)
            }
            cur = dynamics.restore_contributions(cur, event.contributions)
            for rid in event.contributions:
                self._repo.set_region_distortion(session_id, rid, cur[rid])
        event.resolve(session.turn)
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
        event = self._require_event(session_id, event_id)
        if not event.is_suggested():
            raise ValueError(f"only SUGGESTED events can be discarded: {event_id}")
        self._repo.delete_event(session_id, event_id)

    # -- suggest -> approve gate --------------------------------------------
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
                magnitude=clamp(d.magnitude),
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
