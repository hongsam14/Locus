"""U2 K4 — WorldCache: explicit invalidation (EX-18), invalidate-during-load (EX-19),
and one world's load never blocks another world's read."""

from __future__ import annotations

import threading
from datetime import UTC, datetime

from locus.knowledge.cache import WorldCache
from locus.knowledge.loader import WorldLoader
from locus.shared.models import (
    ConnectionEdge,
    ConnectionKind,
    Knowledge,
    KnowledgeGraph,
    Provenance,
    Region,
    RegionLevel,
    RegionTopology,
    ScopeLink,
    ScopeType,
    SourceKind,
    WorldMeta,
    WorldSnapshot,
)
from locus.shared.storage.persistence import persist_graph
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository


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
    # V7 (BR-V7-07, plan § 1.4 R-01): a world without meta was "invalidation only"; it is
    # now never cached, so each read loads it again
    loader.version_value = None
    cache.invalidate("w")
    again = cache.get("w")
    assert cache.get("w") is not again and cache.is_cached("w") is False


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


# --------------------------------------------------------------------------- #
# V7 — a half-replaced world is never cached (BR-V7-07..09)
# --------------------------------------------------------------------------- #
_PROV = Provenance(source=SourceKind.INPUT)


class _ReadMidWrite(InMemoryGraphRepository):
    """Runs ``during_edges`` (a reader in another process) after the nodes are written
    and before the edges are."""

    def __init__(self) -> None:
        super().__init__()
        self.during_edges = None

    def upsert_edges(self, edges) -> None:
        if self.during_edges is not None:
            self.during_edges()
        super().upsert_edges(edges)


def _write_world(graph, stamp: int) -> None:
    a = Region(id="a", world_id="w", name="A", level=RegionLevel.TOWN, provenance=_PROV)
    b = Region(id="b", world_id="w", name="B", level=RegionLevel.TOWN, provenance=_PROV)
    k = Knowledge(id="k", world_id="w", statement="s", title="t", provenance=_PROV)
    persist_graph(
        graph,
        InMemorySearchRepository(),
        None,
        "w",
        regions=[a, b],
        knowledge=[k],
        connections=[
            ConnectionEdge(
                world_id="w",
                source_region_id=x,
                target_region_id=y,
                kind=ConnectionKind.ROUTE,
                weight=0.9,
                provenance=_PROV,
            )
            for x, y in (("a", "b"), ("b", "a"))
        ],
        scopes=[
            ScopeLink(world_id="w", knowledge_id="k", region_id="a", scope_type=ScopeType.DIRECT)
        ],
        meta=WorldMeta(id="w", name="w", updated_at=datetime(2026, 1, stamp, tzinfo=UTC)),
    )


def test_tp_v7_4_a_read_during_another_process_replace_is_not_cached() -> None:
    """RE-W02: the CLI replaces the world while the API reads it between the node and
    the edge writes. That read gets the half world but does not cache it, so the first
    read after the replace sees the connections and scopes."""
    graph = _ReadMidWrite()
    cache = WorldCache(WorldLoader(graph))
    _write_world(graph, 1)
    assert len(cache.get("w").topo.connections) == 2 and cache.is_cached("w")

    seen: dict = {}

    def read() -> None:
        seen["snap"] = cache.get("w")
        seen["cached"] = cache.is_cached("w")

    graph.during_edges = read
    graph.delete_world("w")
    _write_world(graph, 2)
    graph.during_edges = None
    assert seen["snap"].topo.connections == [] and seen["cached"] is False
    after = cache.get("w")
    assert len(after.topo.connections) == 2 and len(after.kg.scopes) == 1
    assert cache.is_cached("w")


def test_tp_v7_5_a_failed_mark_read_on_a_hit_reloads_without_caching() -> None:  # RE-W03
    class _Flaky(_Loader):
        def __init__(self) -> None:
            super().__init__()
            self.fail = False

        def version(self, world_id: str) -> str | None:
            if self.fail:
                raise ConnectionError("graph down for a moment")
            return "v1"

    loader = _Flaky()
    cache = WorldCache(loader)
    first = cache.get("w")
    loader.fail = True
    second = cache.get("w")  # no error for the caller
    assert second is not first and cache.is_cached("w") is False
    loader.fail = False
    third = cache.get("w")
    assert cache.get("w") is third and loader.calls == ["w", "w", "w"]


def test_br_v7_07_a_cache_that_does_not_check_versions_still_caches() -> None:  # § 1.4 R-02
    class _Versioned(_Loader):
        def version(self, world_id: str) -> str | None:
            return None  # would mean "no meta" to a cache that checks

    loader = _Versioned()
    cache = WorldCache(loader, check_version=False)
    first = cache.get("w")
    assert cache.get("w") is first and loader.calls == ["w"]


def test_tp_v7_5_a_mark_read_that_fails_once_still_leaves_nothing_cached() -> None:
    """Code review #21: the mark read fails on the hit, then works for the reload; the
    reloaded snapshot is still served uncached (BLM § 2.2-1)."""

    class _Once(_Loader):
        def __init__(self) -> None:
            super().__init__()
            self.fail_next = False

        def version(self, world_id: str) -> str | None:
            if self.fail_next:
                self.fail_next = False
                raise ConnectionError("graph down for a moment")
            return "v1"

    loader = _Once()
    cache = WorldCache(loader)
    cache.get("w")
    loader.fail_next = True
    cache.get("w")
    assert cache.is_cached("w") is False
