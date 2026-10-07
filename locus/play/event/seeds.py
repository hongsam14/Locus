"""SeedService — a world's event seeds in a session (U8 BLM §3, BR-U8-15..18).

A seed is world data (``WorldSnapshot.event_seeds``). The GM starts one as an ACTIVE
event through ``EventService.create_event``; from then on it is an ordinary event
(turn deltas, propagation, resolve). No LLM is called. Which seed is running is not
stored: an unresolved event whose provenance names the seed is the running one.
"""

from __future__ import annotations

from locus.knowledge.cache import SnapshotSource
from locus.play.base import SessionAppService, names_of, region_name, require_region
from locus.play.errors import SeedAlreadyRunningError
from locus.play.event.service import EventService
from locus.play.models import SeedView, SessionEvent
from locus.play.ports import PlayRepository
from locus.shared.models import EventSeed, Provenance, SourceKind

SEED_SOURCE = "seed"  # SessionEvent.provenance.generated_by of a started seed


class SeedService(SessionAppService):
    def __init__(self, repo: PlayRepository, snapshots: SnapshotSource, events: EventService):
        super().__init__(repo)
        self._snapshots = snapshots
        self._events = events

    def list_seeds(self, session_id: str) -> list[SeedView]:
        """The session world's seeds, by title, each with its running event (closed
        sessions can be read)."""
        session = self._require_session(session_id)
        snapshot = self._snapshots.get(session.world_id)
        names = names_of(snapshot)
        running = self._running(session_id)
        return sorted(
            (
                SeedView(
                    seed=seed,
                    region_name=region_name(names, seed.region_id),
                    running_event_id=running.get(seed.id),
                )
                for seed in snapshot.event_seeds
            ),
            key=lambda v: (v.seed.title, v.seed.id),
        )

    def start(self, session_id: str, seed_id: str) -> SessionEvent:
        """Start ``seed_id`` as an ACTIVE event (BR-U8-15..17). The caller holds the GM
        lease. 409 when closed or when the seed's event is still running."""
        session = self._require_open(session_id)
        snapshot = self._snapshots.get(session.world_id)
        seed = _seed(snapshot.event_seeds, seed_id)
        require_region(self._snapshots, session.world_id, seed.region_id)
        running = self._running(session_id).get(seed.id)
        if running is not None:
            raise SeedAlreadyRunningError(f"seed already running: {seed.id} (event {running})")
        return self._events.create_event(
            session_id,
            seed.region_id,
            category=seed.category,
            magnitude=seed.magnitude,
            description=seed.description or seed.title,
            lifecycle=seed.lifecycle,
            provenance=Provenance(
                source=SourceKind.INPUT, generated_by=SEED_SOURCE, refs=[seed.id]
            ),
            timeline_extra={"seed_id": seed.id, "seed_title": seed.title},
        )

    def _running(self, session_id: str) -> dict[str, str]:
        """seed id -> its unresolved event id in this session."""
        out: dict[str, str] = {}
        for event in self._repo.list_events(session_id, None):
            prov = event.provenance
            if prov.generated_by == SEED_SOURCE and not event.is_resolved():
                for ref in prov.refs:
                    out.setdefault(ref, event.id)
        return out


def _seed(seeds: list[EventSeed], seed_id: str) -> EventSeed:
    for seed in seeds:
        if seed.id == seed_id:
            return seed
    raise LookupError(f"event seed not found: {seed_id}")
