"""WorldCache — one in-memory ``WorldSnapshot`` per world (U2 K4, NFR-3, Q6=A).

Play reads a world on every action; without this each read was a full Neo4j
load. Writers call ``invalidate``; a hit is also re-checked against the world's version
mark (``WorldMeta``), and a world without one is not cached at all (V7, BR-V7-07): its
mark is written last, so "no mark" is a world being replaced, or one built before U2.
No TTL. Single-worker deployment is assumed (each worker would hold its own cache).

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

# The version a loader without ``version()`` (or a cache with ``check_version=False``)
# caches under: such a cache relies on explicit invalidation only, as before V7. Kept
# apart from ``None``, which is a world whose loader can tell it has no mark (R-01).
UNVERSIONED = object()


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
        self._versions: dict[str, object] = {}
        self._gen: dict[str, int] = defaultdict(int)
        self._lock = threading.RLock()
        # A hit is re-checked against the world's cheap version marker (WorldMeta), so a
        # write from another process (the CLI beside a running API) is picked up on the
        # next read instead of never (review U2 #15). A world without meta is not cached
        # (V7, BR-V7-07).
        self._check_version = check_version

    def get(self, world_id: str) -> WorldSnapshot:
        with self._lock:
            hit = self._snapshots.get(world_id)
            cached_version = self._versions.get(world_id)
            gen = self._gen[world_id]
        cacheable = True
        if hit is not None:
            if cached_version is UNVERSIONED:
                return hit
            try:
                if self._current_version(world_id) == cached_version:
                    return hit
            except Exception:
                # RE-W03: a failed mark read on a hit is a miss, not an error for the
                # caller; the reload below is served but not cached.
                logger.warning("world %s version marker unavailable; reloading", world_id)
                cacheable = False
            self.invalidate(world_id)
            with self._lock:
                gen = self._gen[world_id]
        # Read the version marker BEFORE loading: a write that lands during the load
        # then leaves marker != version, so the next read reloads instead of trusting a
        # stale snapshot stamped with the post-write marker (code review U4 #2).
        version: object = UNVERSIONED
        if self._check_version and cacheable:
            try:
                version = self._current_version(world_id)
            except Exception:
                # Unknown marker: serve this read, but do not cache an entry we could
                # never invalidate by version (code review U4-2 #10).
                logger.warning("world %s version marker unavailable; not caching", world_id)
                cacheable = False
        if version is None:
            # No WorldMeta: a world mid-replace (its mark goes in last) or a pre-U2 world.
            # Served, never cached, so the next read sees the finished world (BR-V7-07/08).
            cacheable = False
        snapshot = self._loader.load(world_id)  # outside the lock
        if cacheable:
            with self._lock:
                if self._gen[world_id] == gen:  # no invalidate happened while loading
                    self._snapshots[world_id] = snapshot
                    self._versions[world_id] = version
        return snapshot

    def _current_version(self, world_id: str) -> object:
        """The world's version marker; ``None`` when the world has none (no WorldMeta);
        ``UNVERSIONED`` when this loader cannot tell versions at all.

        Raises when the marker read itself fails: caching an entry as "no marker"
        because of one transient blip disabled the cross-process staleness check for
        that world for the whole process (code review U4-2 #10). The caller serves the
        snapshot but does not cache it.
        """
        version_of = getattr(self._loader, "version", None)
        if version_of is None:
            return UNVERSIONED
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
