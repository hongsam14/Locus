"""U2 K4 — WorldCache: explicit invalidation (EX-18), invalidate-during-load (EX-19),
and one world's load never blocks another world's read."""

from __future__ import annotations

import threading

from locus.knowledge.cache import WorldCache
from locus.shared.models import KnowledgeGraph, RegionTopology, WorldSnapshot


def _snap(world_id: str) -> WorldSnapshot:
    return WorldSnapshot(
        world_id=world_id,
        kg=KnowledgeGraph(world_id=world_id),
        topo=RegionTopology(world_id=world_id),
    )


class _Loader:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.on_load = None  # callback(world_id) run inside load (before returning)

    def load(self, world_id: str) -> WorldSnapshot:
        self.calls.append(world_id)
        if self.on_load:
            self.on_load(world_id)
        return _snap(world_id)


def test_get_caches_until_invalidated() -> None:  # EX-18
    loader = _Loader()
    cache = WorldCache(loader)
    first = cache.get("w")
    assert cache.get("w") is first and loader.calls == ["w"]
    cache.invalidate("w")
    assert cache.get("w") is not first and loader.calls == ["w", "w"]
    assert cache.generation("w") == 1


def test_invalidate_during_load_does_not_cache_the_stale_snapshot() -> None:  # EX-19
    loader = _Loader()
    cache = WorldCache(loader)
    loader.on_load = lambda wid: cache.invalidate(wid)  # a write lands while loading
    snap = cache.get("w")
    assert snap.world_id == "w" and cache.is_cached("w") is False
    loader.on_load = None
    assert cache.get("w") is not snap and cache.is_cached("w") is True


def test_loading_one_world_does_not_block_another() -> None:
    loader = _Loader()
    cache = WorldCache(loader)
    started = threading.Event()
    release = threading.Event()

    def slow(wid: str) -> None:
        if wid == "slow":
            started.set()
            assert release.wait(2.0)

    loader.on_load = slow
    t = threading.Thread(target=cache.get, args=("slow",))
    t.start()
    assert started.wait(2.0)
    assert cache.get("fast").world_id == "fast"  # not blocked by the slow load
    release.set()
    t.join(2.0)
    assert cache.is_cached("slow") and cache.is_cached("fast")


def test_clear_bumps_every_generation() -> None:
    cache = WorldCache(_Loader())
    cache.get("a")
    cache.get("b")
    cache.clear()
    assert not cache.is_cached("a") and cache.generation("a") == 1 and cache.generation("b") == 1


def test_hit_is_refreshed_when_the_world_version_changes() -> None:  # review #15
    class _VersionedLoader(_Loader):
        def __init__(self) -> None:
            super().__init__()
            self.version_value: str | None = "v1"

        def version(self, world_id: str) -> str | None:
            return self.version_value

    loader = _VersionedLoader()
    cache = WorldCache(loader)
    first = cache.get("w")
    assert cache.get("w") is first and loader.calls == ["w"]  # same version: served from cache
    loader.version_value = "v2"  # another process wrote (WorldMeta changed)
    assert cache.get("w") is not first and loader.calls == ["w", "w"]
    loader.version_value = None  # a world without meta: invalidation only
    cache.invalidate("w")
    again = cache.get("w")
    assert cache.get("w") is again


def test_a_write_during_the_load_does_not_poison_the_cache() -> None:  # code review U4 #2
    """The version marker is read BEFORE the load, so a write that lands while the
    snapshot is being read leaves marker != version and the next read reloads."""

    class _WriteDuringLoad(_Loader):
        def __init__(self) -> None:
            super().__init__()
            self.version_value = "v1"

        def version(self, world_id: str) -> str | None:
            return self.version_value

        def load(self, world_id: str) -> WorldSnapshot:
            snap = super().load(world_id)
            self.version_value = "v2"  # another process committed mid-load
            return snap

    loader = _WriteDuringLoad()
    cache = WorldCache(loader)
    stale = cache.get("w")  # cached under v1, the marker seen before loading
    fresh = cache.get("w")  # marker is v2 now -> reload instead of trusting the stale one
    assert fresh is not stale and loader.calls == ["w", "w"]
