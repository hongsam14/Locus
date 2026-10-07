"""EventService — SessionEvent manual lifecycle (Phase 2 / P1+P2).

Owns the operator-facing event lifecycle: create an ACTIVE event, resolve it
(restoring its accumulated distortion), discard a proposal, and the LLM
suggest -> approve gate. The per-turn *application* of active events to
distortion lives in TurnAdvancer; this service is the CRUD/lifecycle boundary.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from locus.knowledge.cache import SnapshotSource
from locus.knowledge.query import region_briefs
from locus.play.base import (
    SessionAppService,
    SnapshotNames,
    names_of,
    region_name,
    require_region,
)
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


class EventService(SnapshotNames, SessionAppService):
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
        provenance: Provenance | None = None,
        timeline_extra: Mapping[str, str] | None = None,
    ) -> SessionEvent:
        """Manually create an ACTIVE event (FR-P2.1). Validates the region (BR-P1-2).

        ``provenance`` and ``timeline_extra`` let a started seed say where the event came
        from (U8, BR-U8-17); a GM's own event keeps the defaults."""
        session = self._require_open(session_id)
        name = require_region(self._snapshots, session.world_id, region_id).name  # C16
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
            provenance=provenance
            or Provenance(source=SourceKind.SIMULATION, generated_by="gm:event"),
        )
        saved = self._repo.create_event(event)
        extra = dict(timeline_extra or {})
        summary = (
            f"started seed {extra['seed_title']!r} in {name}"
            if "seed_title" in extra
            else f"created {cat.value} event in {name}"
        )
        self._timeline(
            session,
            TimelineKind.EVENT_CREATED,
            summary,
            {
                "event_id": saved.id,
                "region_id": region_id,
                "region_name": name,
                "category": cat.value,
                "magnitude": saved.magnitude,
                **extra,
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
        name = self._region_name(session, event.region_id)  # before the transaction (C16)
        # Restore, status and timeline in ONE transaction: a failure part-way used to
        # leave some regions restored while the event stayed ACTIVE, so the next turn
        # accumulated a second contribution and the symmetric restore was permanently
        # broken (code review U4 #4). Deterministic body, no LLM — BR-U4-14 allows it.
        with self._repo.uow() as u:
            # the event as it is now, row locked: a GM set may have cleared a region's
            # contribution since the read above (U3 review #10)
            fresh = u.events.get_event(session_id, event_id, for_update=True)
            if fresh is None:
                raise LookupError(f"event not found: {event_id}")
            if fresh.is_resolved():
                return fresh
            event = fresh
            restored = dict(event.contributions)
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
                    f"resolved {event.category} event in {name}",
                    {
                        "event_id": event_id,
                        "restored": restored,
                        "region_id": event.region_id,
                        "region_name": name,
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
        if not shown:  # a world with no region: nothing to suggest, no call (U7 review §3)
            return []
        every = region_briefs(snapshot, top_k=0)
        drafts = self._suggester.suggest(
            context=ctx.suggestion_context(
                shown, self._event_lines(session, snapshot), self._deed_lines(session)
            ),
            turn=session.turn,
            n=n,
        )
        out: list[SessionEvent] = []
        for d in drafts:
            # by id or unambiguous name among all the world's regions: an event in a region
            # the prompt left out but a line named is still the world's (U7 review §3)
            region_id = ctx.match_region(d.region_id, every)
            if region_id is None:  # not a region of this world (BR-P2-10)
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
                "category": EventCategory(event.category).value,
            },
        )
        return saved

    # -- internals -----------------------------------------------------------
    def _require_event(self, session_id: str, event_id: str) -> SessionEvent:
        event = self._repo.get_event(session_id, event_id)
        if event is None:
            raise LookupError(f"event not found: {event_id}")
        return event

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
            parent_ids={r.parent_id for r in snapshot.topo.regions if r.parent_id},
        )

    def _event_lines(self, session: GameSession, snapshot) -> list[str]:
        """The latest five events that are not mere suggestions, newest first."""
        names = names_of(snapshot)
        events = [e for e in self._repo.list_events(session.id) if not e.is_suggested()]
        events.sort(key=lambda e: (e.created_turn, e.id), reverse=True)
        return [
            ctx.event_line(
                region_name(names, e.region_id),
                EventCategory(e.category).value,
                e.magnitude,
                EventStatus(e.status).value,  # an enum member in memory (U7 review #13)
                e.description,
            )
            for e in events[:5]
        ]

    def _deed_lines(self, session: GameSession) -> list[str]:
        """Recent deeds for the suggestion prompt (U6 BR-U6-31; FR-D2 보강): what the
        traveler did lately can give rise to events. Voided deeds are left out."""
        if self._deeds is None:
            return []
        names = names_of(self._snapshots.get(session.world_id))
        lines = []
        for deed, appraisals in self._deeds.recent(session.id, 5):
            told = next((a.retelling for a in appraisals if a.noteworthy and a.retelling), None)
            lines.append(ctx.deed_line(region_name(names, deed.region_id), deed.text, told))
        return lines
