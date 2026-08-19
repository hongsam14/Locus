"""In-memory SessionRepository — offline tests / mock (NFR-R1, C4).

Dict-based; satisfies the full port contract with the same visible behaviour as
the PostgreSQL adapter (ordering, session isolation, idempotent close). A
monotonic counter stands in for DB server time so ordering is deterministic
(BR-S1-8).
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from .models import (
    GameSession,
    RegionDistortion,
    SessionEvent,
    SessionRumor,
    SessionStatus,
    TimelineEntry,
    Translation,
)


class InMemorySessionRepository:
    """A process-local SessionRepository for tests and offline use."""

    def __init__(self) -> None:
        self._sessions: dict[str, GameSession] = {}
        self._rumors: dict[str, dict[str, SessionRumor]] = {}  # session_id -> {rumor_id: rumor}
        self._distortions: dict[tuple[str, str], float] = {}  # (session_id, region_id) -> degree
        self._timeline: dict[str, list[TimelineEntry]] = {}  # session_id -> entries
        self._events: dict[str, dict[str, SessionEvent]] = {}  # session_id -> {event_id: event}
        # (kind, source_id, field, lang) -> Translation (X1 localization cache)
        self._translations: dict[tuple[str, str, str, str], Translation] = {}
        self._clock = 0

    # --- internal ---
    def _now(self) -> datetime:
        # Strictly increasing fake server time for deterministic ordering.
        self._clock += 1
        return datetime.fromtimestamp(self._clock, tz=timezone.utc)

    # --- lifecycle ---
    def connect(self) -> None:  # no-op
        return None

    def disconnect(self) -> None:  # no-op
        return None

    def health_check(self) -> bool:
        return True

    def ensure_schema(self) -> None:  # no-op
        return None

    # --- sessions ---
    def create_session(self, world_id: str) -> GameSession:
        session = GameSession(
            world_id=world_id,
            status=SessionStatus.OPEN,
            turn=0,
            created_at=self._now(),
        )
        self._sessions[session.id] = session
        self._rumors[session.id] = {}
        self._timeline[session.id] = []
        self._events[session.id] = {}
        return deepcopy(session)

    def get_session(self, session_id: str) -> GameSession | None:
        s = self._sessions.get(session_id)
        return deepcopy(s) if s else None

    def list_sessions(self, world_id: str) -> list[GameSession]:
        out = [deepcopy(s) for s in self._sessions.values() if s.world_id == world_id]
        out.sort(key=lambda s: s.created_at or datetime.min.replace(tzinfo=timezone.utc))
        return out

    def close_session(self, session_id: str) -> GameSession:
        s = self._require_session(session_id)
        if s.status != SessionStatus.CLOSED.value:
            s.status = SessionStatus.CLOSED.value
            s.closed_at = self._now()
        return deepcopy(s)

    def bump_turn(self, session_id: str) -> int:
        s = self._require_session(session_id)
        s.turn += 1
        return s.turn

    # --- rumors ---
    def upsert_rumor(self, rumor: SessionRumor) -> SessionRumor:
        self._require_session(rumor.session_id)
        self._rumors[rumor.session_id][rumor.id] = deepcopy(rumor)
        return deepcopy(rumor)

    def upsert_rumors(self, rumors: list[SessionRumor]) -> list[SessionRumor]:
        """Batch upsert in one logical write (FR-H5). Returns the stored rumors."""
        return [self.upsert_rumor(r) for r in rumors]

    def get_rumor(self, session_id: str, rumor_id: str) -> SessionRumor | None:
        r = self._rumors.get(session_id, {}).get(rumor_id)
        return deepcopy(r) if r else None

    def list_rumors(
        self, session_id: str, region_id: str | None = None, *, include_pruned: bool = False
    ) -> list[SessionRumor]:
        rumors = self._rumors.get(session_id, {}).values()
        return [
            deepcopy(r)
            for r in rumors
            if (region_id is None or r.region_id == region_id) and (include_pruned or r.active)
        ]

    def delete_rumor(self, session_id: str, rumor_id: str) -> None:
        self._rumors.get(session_id, {}).pop(rumor_id, None)

    # --- region distortion ---
    def set_region_distortion(self, session_id: str, region_id: str, degree: float) -> None:
        self._require_session(session_id)
        self._distortions[(session_id, region_id)] = degree

    def get_region_distortion(self, session_id: str, region_id: str) -> float | None:
        return self._distortions.get((session_id, region_id))

    def list_region_distortions(self, session_id: str) -> list[RegionDistortion]:
        return [
            RegionDistortion(session_id=sid, region_id=rid, distortion_degree=deg)
            for (sid, rid), deg in self._distortions.items()
            if sid == session_id
        ]

    # --- timeline ---
    def append_timeline(self, entry: TimelineEntry) -> TimelineEntry:
        self._require_session(entry.session_id)
        stored = deepcopy(entry)
        if stored.created_at is None:
            stored.created_at = self._now()
        self._timeline[entry.session_id].append(stored)
        return deepcopy(stored)

    def list_timeline(self, session_id: str) -> list[TimelineEntry]:
        entries = self._timeline.get(session_id, [])
        ordered = sorted(
            entries,
            key=lambda e: (e.turn, e.created_at or datetime.min.replace(tzinfo=timezone.utc)),
        )
        return [deepcopy(e) for e in ordered]

    # --- events (Phase 2) ---
    def create_event(self, event: SessionEvent) -> SessionEvent:
        self._require_session(event.session_id)
        self._events.setdefault(event.session_id, {})[event.id] = deepcopy(event)
        return deepcopy(event)

    def get_event(self, session_id: str, event_id: str) -> SessionEvent | None:
        e = self._events.get(session_id, {}).get(event_id)
        return deepcopy(e) if e else None

    def list_events(self, session_id: str, status: str | None = None) -> list[SessionEvent]:
        events = self._events.get(session_id, {}).values()
        out = [deepcopy(e) for e in events if status is None or e.status == status]
        out.sort(key=lambda e: (e.created_turn, e.id))
        return out

    def update_event(self, event: SessionEvent) -> SessionEvent:
        self._require_session(event.session_id)
        self._events.setdefault(event.session_id, {})[event.id] = deepcopy(event)
        return deepcopy(event)

    def delete_event(self, session_id: str, event_id: str) -> None:
        self._events.get(session_id, {}).pop(event_id, None)

    # --- translations (X1) ---
    def get_translation(
        self, source_kind: str, source_id: str, source_field: str, target_lang: str
    ) -> Translation | None:
        t = self._translations.get((source_kind, source_id, source_field, target_lang))
        return deepcopy(t) if t else None

    def get_translations_many(
        self, keys: list[tuple[str, str, str]], target_lang: str
    ) -> dict[tuple[str, str], Translation]:
        out: dict[tuple[str, str], Translation] = {}
        for kind, source_id, field in keys:
            t = self._translations.get((kind, source_id, field, target_lang))
            if t is not None:
                out[(source_id, field)] = deepcopy(t)
        return out

    def upsert_translation(self, translation: Translation) -> Translation:
        key = (
            translation.source_kind,
            translation.source_id,
            translation.source_field,
            translation.target_lang,
        )
        stored = deepcopy(translation)
        if stored.created_at is None:
            stored.created_at = self._now()
        self._translations[key] = stored
        return deepcopy(stored)

    def upsert_translations(self, translations: list[Translation]) -> list[Translation]:
        return [self.upsert_translation(t) for t in translations]

    # --- helpers ---
    def _require_session(self, session_id: str) -> GameSession:
        s = self._sessions.get(session_id)
        if s is None:
            raise KeyError(f"session not found: {session_id}")
        return s
