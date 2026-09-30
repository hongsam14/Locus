"""WorldCache — one in-memory ``WorldSnapshot`` per world (U2 K4, NFR-3, Q6=A).

Play reads a world on every action; without this each read was a full Neo4j
load. Explicit invalidation only (bulk writers call ``invalidate``); no TTL.
Single-worker deployment is assumed (each worker would hold its own cache).

The load runs outside the lock so one world's load never blocks another
world's read, and a per-world generation counter makes "invalidate during a
load" safe: a snapshot loaded from a generation that has since been
invalidated is returned to the caller but not cached (BR-U2-17).
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Protocol

from locus.knowledge.loader import WorldLoader
from locus.shared.models import WorldSnapshot

logger = logging.getLogger(__name__)


class SnapshotSource(Protocol):
    """Anything that yields the current ``WorldSnapshot`` of a world (cache or loader)."""

    def get(self, world_id: str) -> WorldSnapshot: ...


class SnapshotCache(SnapshotSource, Protocol):
    """A ``SnapshotSource`` that writers can invalidate (the ``WorldCache``)."""

    def invalidate(self, world_id: str) -> None: ...


class WorldCache:
    def __init__(self, loader: WorldLoader, *, check_version: bool = True) -> None:
        self._loader = loader
        self._snapshots: dict[str, WorldSnapshot] = {}
        self._versions: dict[str, str | None] = {}
        self._gen: dict[str, int] = defaultdict(int)
        self._lock = threading.RLock()
        # A hit is re-checked against the world's cheap version marker (WorldMeta), so a
        # write from another process (the CLI beside a running API) is picked up on the
        # next read instead of never (review U2 #15). Worlds without meta rely on
        # explicit invalidation only.
        self._check_version = check_version

    def get(self, world_id: str) -> WorldSnapshot:
        with self._lock:
            hit = self._snapshots.get(world_id)
            cached_version = self._versions.get(world_id)
            gen = self._gen[world_id]
        if hit is not None:
            if not self._check_version or cached_version is None:
                return hit
            if self._current_version(world_id) == cached_version:
                return hit
            self.invalidate(world_id)
            with self._lock:
                gen = self._gen[world_id]
        # Read the version marker BEFORE loading: a write that lands during the load
        # then leaves marker != version, so the next read reloads instead of trusting a
        # stale snapshot stamped with the post-write marker (code review U4 #2).
        version: str | None = None
        cacheable = True
        if self._check_version:
            try:
                version = self._current_version(world_id)
            except Exception:
                # Unknown marker: serve this read, but do not cache an entry we could
                # never invalidate by version (code review U4-2 #10).
                logger.warning("world %s version marker unavailable; not caching", world_id)
                cacheable = False
        snapshot = self._loader.load(world_id)  # outside the lock
        if cacheable:
            with self._lock:
                if self._gen[world_id] == gen:  # no invalidate happened while loading
                    self._snapshots[world_id] = snapshot
                    self._versions[world_id] = version
        return snapshot

    def _current_version(self, world_id: str) -> str | None:
        """The world's version marker, ``None`` when this loader has none.

        Raises when the marker read itself fails: caching an entry as "no marker"
        because of one transient blip disabled the cross-process staleness check for
        that world for the whole process (code review U4-2 #10). The caller serves the
        snapshot but does not cache it.
        """
        version_of = getattr(self._loader, "version", None)
        if version_of is None:
            return None
        return version_of(world_id)

    def invalidate(self, world_id: str) -> None:
        with self._lock:
            self._snapshots.pop(world_id, None)
            self._versions.pop(world_id, None)
            self._gen[world_id] += 1

    def clear(self) -> None:
        with self._lock:
            for world_id in set(self._gen) | set(self._snapshots):
                self._gen[world_id] += 1
            self._snapshots.clear()
            self._versions.clear()

    def generation(self, world_id: str) -> int:
        """How many times ``world_id`` was invalidated (tests / diagnostics)."""
        with self._lock:
            return self._gen[world_id]

    def is_cached(self, world_id: str) -> bool:
        with self._lock:
            return world_id in self._snapshots
