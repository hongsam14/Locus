"""EventService — SessionEvent manual lifecycle (Phase 2 / P1+P2).

Owns the operator-facing event lifecycle: create an ACTIVE event, resolve it
(restoring its accumulated distortion), discard a proposal, and the LLM
suggest -> approve gate. The per-turn *application* of active events to
distortion lives in TurnAdvancer; this service is the CRUD/lifecycle boundary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from locus.knowledge.cache import SnapshotSource
from locus.knowledge.query import region_briefs
from locus.play.base import SessionAppService, require_region
from locus.play.errors import InvalidActionError, LlmUnavailableError
from locus.play.event import dynamics
from locus.play.event import suggest_context as ctx
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
from locus.shared.config.tuning import PlayTuning
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
        tuning: PlayTuning | None = None,
    ) -> None:
        super().__init__(repo)
        self._snapshots = snapshots
        self._tuning = tuning or PlayTuning()  # n cap and prompt size (U7, BR-U7-9/10)
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
        name = self._region_name(session, region_id)
        self._timeline(
            session,
            TimelineKind.EVENT_CREATED,
            f"created {cat.value} event in {name}",
            {
                "event_id": saved.id,
                "region_id": region_id,
                "region_name": name,
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
        if event.is_suggested():  # approve first (BR-U7-7, RE C5)
            raise InvalidActionError(f"a suggested event must be approved first: {event_id}")
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
                    f"resolved {event.category} event in "
                    f"{self._region_name(session, event.region_id)}",
                    {
                        "event_id": event_id,
                        "restored": restored,
                        "region_id": event.region_id,
                        "region_name": self._region_name(session, event.region_id),
                    },
                )
            )
        return saved

    def discard_event(self, session_id: str, event_id: str) -> None:
        """Discard a SUGGESTED event (BR-P1-8). ACTIVE/RESOLVED cannot be discarded."""
        session = self._require_open(session_id)
        event = self._require_event(session_id, event_id)
        if not event.is_suggested():
            raise ValueError(f"only SUGGESTED events can be discarded: {event_id}")
        name = self._region_name(session, event.region_id)
        # The line first, in the same unit of work: the row is gone afterwards, so the
        # line keeps what was discarded (BR-U7-8, FR-E4).
        with self._repo.uow() as u:
            u.timeline.append_timeline(
                self._entry(
                    session,
                    TimelineKind.EVENT_DISCARDED,
                    f"discarded the {event.category} suggestion in {name}",
                    {
                        "event_id": event_id,
                        "region_id": event.region_id,
                        "region_name": name,
                        "category": str(event.category),
                        "description": event.description,
                    },
                )
            )
            u.events.delete_event(session_id, event_id)

    # -- suggest -> approve gate --------------------------------------------
    def suggest_events(self, session_id: str, *, n: int = 1) -> list[SessionEvent]:
        """LLM proposes up to ``n`` events, persisted as SUGGESTED (FR-P2.2, BR-P2-10).

        U7 (BR-U7-9/10): ``n`` is 1..``max_event_suggestions`` (400 otherwise, before any
        LLM call), and the prompt sees the world — region names, places, descriptions and
        known facts, recent events and deeds — under a "material" heading. A draft's
        region is found by id, else by the name the prompt showed. Needs a provider (503
        without one); an LLM failure is graceful -> [].
        """
        limit = self._tuning.max_event_suggestions
        if not 1 <= n <= limit:
            raise InvalidActionError(f"n must be between 1 and {limit}: {n}")
        if self._suggester is None:
            raise LlmUnavailableError("event suggestion needs an LLM provider (set OPENAI_API_KEY)")
        session = self._require_open(session_id)
        snapshot = self._snapshots.get(session.world_id)
        shown = self._shown_regions(session, snapshot)
        drafts = self._suggester.suggest(
            context=ctx.suggestion_context(
                shown, self._event_lines(session, snapshot), self._deed_lines(session)
            ),
            turn=session.turn,
            n=n,
        )
        out: list[SessionEvent] = []
        for d in drafts:
            region_id = ctx.match_region(d.region_id, shown)
            if region_id is None:  # skip a region the prompt did not show (BR-P2-10)
                continue
            cat = EventCategory(d.category)
            event = SessionEvent(
                session_id=session_id,
                region_id=region_id,
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
            name = self._region_name(session, region_id)
            self._timeline(
                session,
                TimelineKind.EVENT_SUGGESTED,
                f"suggested {cat.value} event in {name}",
                {
                    "event_id": saved.id,
                    "region_id": region_id,
                    "region_name": name,
                    "category": cat.value,
                    "magnitude": saved.magnitude,
                    "description": saved.description,
                },
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
        name = self._region_name(session, event.region_id)
        self._timeline(
            session,
            TimelineKind.EVENT_APPROVED,
            f"approved the {event.category} event in {name}",
            {
                "event_id": event_id,
                "region_id": event.region_id,
                "region_name": name,
                "category": str(event.category),
            },
        )
        return saved

    # -- internals -----------------------------------------------------------
    def _require_event(self, session_id: str, event_id: str) -> SessionEvent:
        event = self._repo.get_event(session_id, event_id)
        if event is None:
            raise LookupError(f"event not found: {event_id}")
        return event

    def _region_name(self, session: GameSession, region_id: str) -> str:
        """FR-D3: lines name regions; the id stands in when the world lost the region."""
        region = self._snapshots.get(session.world_id).regions_by_id.get(region_id)
        return region.name if region is not None else region_id

    def _shown_regions(self, session: GameSession, snapshot) -> list:
        """The regions the suggestion prompt shows, in the FD review R-06 order."""
        player = self._repo.get_player(session.id)
        events = self._repo.list_events(session.id, EventStatus.ACTIVE.value)
        counts: dict[str, int] = {}
        for r in self._repo.list_rumors(session.id):
            counts[r.region_id] = counts.get(r.region_id, 0) + 1
        return ctx.pick_brief_regions(
            region_briefs(snapshot, top_k=ctx.KNOWLEDGE_PER_REGION),
            player_region_id=player.region_id if player is not None else None,
            event_region_ids={e.region_id for e in events},
            rumor_counts=counts,
            limit=self._tuning.suggest_max_regions,
        )

    def _event_lines(self, session: GameSession, snapshot) -> list[str]:
        """The latest five events that are not mere suggestions, newest first."""
        names = {r.id: r.name for r in snapshot.topo.regions}
        events = [
            e
            for e in self._repo.list_events(session.id)
            if str(e.status) != EventStatus.SUGGESTED.value
        ]
        events.sort(key=lambda e: (e.created_turn, e.id), reverse=True)
        return [
            ctx.event_line(
                names.get(e.region_id, e.region_id),
                str(e.category),
                e.magnitude,
                str(e.status),
                e.description,
            )
            for e in events[:5]
        ]

    def _deed_lines(self, session: GameSession) -> list[str]:
        """Recent deeds for the suggestion prompt (U6 BR-U6-31; FR-D2 보강): what the
        traveler did lately can give rise to events. Voided deeds are left out."""
        if self._deeds is None:
            return []
        names = {r.id: r.name for r in self._snapshots.get(session.world_id).topo.regions}
        lines = []
        for deed, appraisals in self._deeds.recent(session.id, 5):
            told = next((a.retelling for a in appraisals if a.noteworthy and a.retelling), None)
            lines.append(ctx.deed_line(names.get(deed.region_id, deed.region_id), deed.text, told))
        return lines
