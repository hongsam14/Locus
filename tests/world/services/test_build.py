"""U2 Step 8 — WorldBuilder.build: prepare/commit (EX-10/11/12), ok semantics (EX-14),
unscoped knowledge (EX-15), per-build call counting (EX-16)."""

from __future__ import annotations

import json

import pytest

from locus.knowledge.cache import WorldCache
from locus.knowledge.loader import WorldLoader
from locus.shared.models import (
    BuildWarning,
    IngestionResult,
    Knowledge,
    KnowledgeGraph,
    Provenance,
    Region,
    RegionLevel,
    RegionTopology,
    SourceKind,
)
from locus.world.build import BuildProviders, WorldBuilder, WorldExistsError
from locus.world.ontology.builder import OntologyBuild
from locus.world.topology.builder import TopologyBuild
from locus.world.worldfile.export import WorldFileExporter
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


class _Ingest:
    def __init__(self, *, regions=1, fail: Exception | None = None, warnings=()) -> None:
        self.regions, self.fail, self.warnings = regions, fail, list(warnings)

    def ingest_all(self, world_id, inputs):
        if self.fail:
            raise self.fail
        hints = [
            Region(world_id=world_id, name=f"R{i}", level=RegionLevel.TOWN, provenance=_prov())
            for i in range(self.regions)
        ]
        k = Knowledge(
            world_id=world_id, statement="fact", title="Fact", region_hint="R0", provenance=_prov()
        )
        lost = Knowledge(
            world_id=world_id,
            statement="lost",
            title="Lost",
            region_hint="Nowhere",
            provenance=_prov(),
        )
        return IngestionResult(
            world_id=world_id, region_hints=hints, knowledge=[k, lost], warnings=self.warnings
        )


class _Topo:
    def build(self, ingestion, *, world_id):
        return TopologyBuild(
            RegionTopology(world_id=world_id, regions=list(ingestion.region_hints))
        )


class _Onto:
    def __init__(self, llm=None, embedding=None) -> None:
        self.llm, self.embedding = llm, embedding

    def build(self, ingestion, topology, *, world_id):
        if self.llm is not None:
            self.llm.complete("corroborate")  # counted (EX-16)
        if self.embedding is not None:
            self.embedding.embed(["x"])
        kg = KnowledgeGraph(world_id=world_id, knowledge=list(ingestion.knowledge))
        from locus.shared.models import ScopeLink, ScopeType

        for k in ingestion.knowledge:
            if k.region_hint == "R0" and topology.regions:
                kg.scopes.append(
                    ScopeLink(
                        world_id=world_id,
                        knowledge_id=k.id,
                        region_id=topology.regions[0].id,
                        scope_type=ScopeType.DIRECT,
                    )
                )
            else:
                kg.unscoped_knowledge_ids.append(k.id)
        return OntologyBuild(
            kg=kg, warnings=[BuildWarning(stage="ontology", message="unresolved: Nowhere")]
        )


class _LLM:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, prompt, *, system=None):
        self.calls += 1
        return "ok"

    def structured(self, prompt, schema, *, system=None):  # pragma: no cover
        self.calls += 1
        return schema()


class _Emb:
    def __init__(self) -> None:
        self.calls = 0

    @property
    def dimension(self) -> int:
        return 2

    def embed(self, texts):
        self.calls += 1
        return [[0.0, 1.0] for _ in texts]


def _make(
    tmp_path, *, graph=None, search=None, ingest=None, llm=None, emb=None, exporter="default"
):
    graph = graph or InMemoryGraphRepository()
    search = search or InMemorySearchRepository()
    cache = WorldCache(WorldLoader(graph))
    builder = WorldBuilder(
        graph,
        search,
        cache,
        providers=BuildProviders(llm=llm, vlm=None, embedding=emb),
        ingestion_factory=lambda llm_, vlm_: ingest or _Ingest(),
        topology_factory=lambda wiki: _Topo(),
        ontology_factory=lambda llm_, emb_, wiki: _Onto(llm_, emb_),
        exporter=WorldFileExporter(cache) if exporter == "default" else exporter,
        backup_dir=tmp_path / "backups" if exporter is not None else None,
    )
    return builder, graph, search, cache


def test_build_persists_and_reports_unscoped(tmp_path) -> None:  # EX-15
    builder, graph, _s, cache = _make(tmp_path)
    report = builder.build("w", inputs=None, replace=True)
    assert report.ok and report.regions_created == 1 and report.replaced is False
    assert len(report.unscoped_knowledge_ids) == 1
    snap = cache.get("w")
    assert snap.unscoped_knowledge_ids == report.unscoped_knowledge_ids  # stored, visible
    assert snap.meta is not None and snap.meta.last_writer == "build"
    assert any("Nowhere" in w.message for w in report.warnings)


def test_replace_false_on_existing_world_raises(tmp_path) -> None:  # EX-12
    builder, *_ = _make(tmp_path)
    builder.build("w", inputs=None)
    with pytest.raises(WorldExistsError):
        builder.build("w", inputs=None, replace=False)


def test_prepare_failure_keeps_the_old_world(tmp_path) -> None:  # EX-10
    builder, graph, _s, cache = _make(tmp_path)
    builder.build("w", inputs=None)
    before = {n.id for n in graph.find_nodes("w", "Region")}
    broken, *_ = _make(tmp_path, graph=graph, ingest=_Ingest(fail=RuntimeError("llm down")))
    with pytest.raises(RuntimeError):
        broken.build("w", inputs=None, replace=True)
    assert {n.id for n in graph.find_nodes("w", "Region")} == before  # untouched
    report = _make(tmp_path, graph=graph, ingest=_Ingest(regions=0))[0].build("w", inputs=None)
    assert report.ok is False and report.replaced is False  # "no regions" -> prepare-phase error
    assert {n.id for n in graph.find_nodes("w", "Region")} == before


def test_commit_failure_reports_replaced_and_backs_up(tmp_path) -> None:  # EX-11
    builder, graph, search, cache = _make(tmp_path)
    builder.build("w", inputs=None)
    gen_before = cache.generation("w")
    cache.get("w")
    graph.fail_on_upsert = RuntimeError("neo4j down")
    report = builder.build("w", inputs=None, replace=True)
    assert report.ok is False and report.replaced is True
    assert report.errors and report.errors[0].stage == "persist-graph"
    backups = list((tmp_path / "backups").glob("w-*.world.json"))
    assert len(backups) == 1 and json.loads(backups[0].read_text())["world_id"] == "w"
    assert cache.generation("w") > gen_before and not cache.is_cached("w")


def test_ok_follows_error_paths_only(tmp_path) -> None:  # EX-14
    warn = BuildWarning(stage="ingestion", message="item skipped")
    builder, *_ = _make(tmp_path, ingest=_Ingest(warnings=[warn]))
    assert builder.build("w", inputs=None).ok is True  # warnings alone keep ok
    unreadable = BuildWarning(stage="ingestion", severity="error", message="bad base64")
    builder2, *_ = _make(tmp_path, ingest=_Ingest(warnings=[unreadable]))
    assert builder2.build("w2", inputs=None).ok is False
    search = InMemorySearchRepository()
    search.fail_on_index = RuntimeError("opensearch down")
    builder3, *_ = _make(tmp_path, search=search)
    assert builder3.build("w3", inputs=None).ok is False


def test_llm_and_embedding_calls_are_counted_per_build(tmp_path) -> None:  # EX-16
    llm, emb = _LLM(), _Emb()
    builder, *_ = _make(tmp_path, llm=llm, emb=emb)
    first = builder.build("w", inputs=None)
    second = builder.build("w", inputs=None, replace=True)
    assert first.llm_calls == 1 and first.embedding_calls >= 1
    assert second.llm_calls == 1  # counted per build, not cumulative
    assert llm.calls == 2 and emb.calls == first.embedding_calls + second.embedding_calls


def test_commit_failure_after_delete_is_reported_not_raised(tmp_path) -> None:  # review #2
    builder, graph, search, cache = _make(tmp_path)
    builder.build("w", inputs=None)

    def boom(world_id):
        raise RuntimeError("opensearch down")

    search.delete_world = boom  # type: ignore[method-assign]
    report = builder.build("w", inputs=None, replace=True)
    assert report.ok is False and report.replaced is True
    assert report.errors[0].stage == "commit" and "restore from backup" in report.errors[0].message
    assert report.backup_path and report.backup_path.endswith(".world.json")
    assert not cache.is_cached("w")


def test_replace_build_drops_prior_refs_into_the_old_world(tmp_path) -> None:  # review #14
    from locus.shared.models import ConnectionEdge, ConnectionKind

    class _TopoWithRef(_Topo):
        def build(self, ingestion, *, world_id):
            regions = list(ingestion.region_hints)
            edge = ConnectionEdge(
                world_id=world_id,
                source_region_id=regions[0].id,
                target_region_id=regions[0].id,
                kind=ConnectionKind.ROUTE,
                weight=0.5,
                rationale="mountains",
                wiki_prior_ref="old-prior",
                provenance=_prov(),
            )
            return TopologyBuild(
                RegionTopology(world_id=world_id, regions=regions, connections=[edge])
            )

    builder, graph, _s, cache = _make(tmp_path)
    builder._topology_factory = lambda wiki: _TopoWithRef()
    report = builder.build("w", inputs=None)
    conn = cache.get("w").topo.connections[0]
    assert conn.wiki_prior_ref is None and conn.rationale == "mountains"
    assert any("prior ref belonged" in w.message for w in report.warnings)


def test_u8_review_2_one_build_per_world_at_a_time(tmp_path) -> None:
    """U8 review #2: a second build of the same world while the first is still preparing
    (a reopened panel, a retry after a proxy timeout) is refused instead of committing a
    second copy; another world builds alongside; after the first ends, the world builds."""
    import threading

    from locus.world.build import BuildInProgressError

    started, release = threading.Event(), threading.Event()

    class _Slow(_Ingest):
        def ingest_all(self, world_id, inputs):
            if world_id == "w" and not release.is_set():
                started.set()
                release.wait(5)
            return super().ingest_all(world_id, inputs)

    builder, graph, _s, _c = _make(tmp_path, ingest=_Slow())
    first: dict = {}
    worker = threading.Thread(target=lambda: first.update(r=builder.build("w", inputs=None)))
    worker.start()
    assert started.wait(5)
    with pytest.raises(BuildInProgressError, match="already running"):
        builder.build("w", inputs=None)
    assert builder.build("other", inputs=None).ok  # another world is not held up
    release.set()
    worker.join(5)
    assert first["r"].ok
    regions = graph.find_nodes("w", "Region")
    assert len(regions) == 1  # one copy, not two
    assert builder.build("w", inputs=None).ok  # the world is free again


def test_u8_review_2_a_failed_build_frees_its_world(tmp_path) -> None:
    builder, *_ = _make(tmp_path, ingest=_Ingest(fail=RuntimeError("ingest broke")))
    with pytest.raises(RuntimeError, match="ingest broke"):
        builder.build("w", inputs=None)
    builder._ingestion_factory = lambda llm_, vlm_: _Ingest()  # type: ignore[assignment]
    assert builder.build("w", inputs=None).ok


# --------------------------------------------------------------------------- #
# V7 — a failed backup stops the replace before anything is deleted (TP-V7-7)
# --------------------------------------------------------------------------- #
class _BrokenExporter:
    def export_world(self, world_id):
        raise OSError("disk full")


def test_tp_v7_7_a_failed_backup_leaves_the_old_world(tmp_path) -> None:
    builder, graph, _search, cache = _make(tmp_path)
    builder.build("w", inputs=None)
    old = sorted((n.label, n.id) for n in graph._nodes.values())
    deleted: list = []
    real_delete = graph.delete_world
    graph.delete_world = lambda wid: (deleted.append(wid), real_delete(wid))  # type: ignore

    broken, *_ = _make(tmp_path, graph=graph, exporter=_BrokenExporter())
    report = broken.build("w", inputs=None, replace=True)

    assert report.ok is False and report.replaced is False and report.backup_path is None
    assert [(w.stage, w.severity) for w in report.errors] == [("backup", "error")]
    assert "not replaced" in report.errors[0].message and "disk full" in report.errors[0].message
    assert deleted == [] and sorted((n.label, n.id) for n in graph._nodes.values()) == old
    assert len(cache.get("w").topo.regions) == 1


def test_br_v7_11_a_builder_without_a_backup_still_replaces(tmp_path) -> None:
    builder, graph, *_ = _make(tmp_path, exporter=None)
    builder.build("w", inputs=None)
    report = builder.build("w", inputs=None, replace=True)
    assert report.ok and report.replaced is True and report.backup_path is None


# --------------------------------------------------------------------------- #
# V7 — a rebuild keeps the world's NPCs and event seeds (TP-V7-8, TP-V7-9)
# --------------------------------------------------------------------------- #
def _add_people(graph, regions_by_name: dict, *, npc_homes=("R0", "R1"), seed_home="R1"):
    """What the editor would add after a build: NPCs and an event seed."""
    from locus.shared.models import NPC, EventSeed
    from locus.shared.storage.persistence import persist_graph

    npcs = [
        NPC(
            id=f"npc-{i}",
            world_id="w",
            name=f"Npc {i}",
            role="miller",
            description="d",
            home_region_id=regions_by_name[home],
            provenance=_prov(),
        )
        for i, home in enumerate(npc_homes)
    ]
    seed = EventSeed(
        id="seed-0",
        world_id="w",
        region_id=regions_by_name[seed_home],
        title="Flood",
        category="disaster",
        magnitude=0.5,
        provenance=_prov(),
    )
    persist_graph(graph, InMemorySearchRepository(), None, "w", npcs=npcs, seeds=[seed])
    return npcs, seed


def _names(cache) -> dict:
    return {r.name: r.id for r in cache.get("w").topo.regions}


def test_tp_v7_8_a_rebuild_carries_npcs_and_seeds_onto_the_new_regions(tmp_path) -> None:
    builder, graph, _search, cache = _make(tmp_path, ingest=_Ingest(regions=2))
    builder.build("w", inputs=None)
    old_ids = _names(cache)
    _add_people(graph, old_ids)
    cache.invalidate("w")

    report = builder.build("w", inputs=None, replace=True)

    assert report.ok and report.replaced is True
    assert (report.carried_npcs, report.carried_seeds) == (2, 1)
    after = cache.get("w")
    new_ids = _names(cache)
    assert set(new_ids.values()).isdisjoint(old_ids.values())  # new regions
    homes = {n.id: n.home_region_id for n in after.npcs}
    assert homes == {"npc-0": new_ids["R0"], "npc-1": new_ids["R1"]}
    assert [(s.id, s.region_id) for s in after.event_seeds] == [("seed-0", new_ids["R1"])]


def test_tp_v7_8_an_npc_whose_region_is_gone_is_named_not_carried(tmp_path) -> None:
    builder, graph, _search, cache = _make(tmp_path, ingest=_Ingest(regions=2))
    builder.build("w", inputs=None)
    _add_people(graph, _names(cache))
    cache.invalidate("w")
    shrunk, *_ = _make(tmp_path, graph=graph, ingest=_Ingest(regions=1))  # no R1 now

    report = shrunk.build("w", inputs=None, replace=True)

    assert report.ok and (report.carried_npcs, report.carried_seeds) == (1, 0)
    left = [w for w in report.warnings if w.stage == "carry-over"]
    assert sorted(w.item_id for w in left) == ["npc-1", "seed-0"]
    assert all(w.severity == "warning" for w in left)


def test_tp_v7_9_the_old_world_is_read_fresh_not_from_the_cache(tmp_path) -> None:
    """The cache still holds the world as it was before the editor's NPC (same version
    mark: the NPC went in without touching WorldMeta); the rebuild reads it fresh."""
    builder, graph, _search, cache = _make(tmp_path, ingest=_Ingest(regions=2))
    builder.build("w", inputs=None)
    assert cache.get("w").npcs == [] and cache.is_cached("w")
    _add_people(graph, _names(cache))
    assert cache.get("w").npcs == []  # stale on purpose

    report = builder.build("w", inputs=None, replace=True)

    assert report.carried_npcs == 2 and len(cache.get("w").npcs) == 2


def test_tp_v7_9_an_old_world_that_cannot_be_read_is_not_replaced(tmp_path) -> None:
    class _Unreadable(WorldCache):
        fail = False

        def get(self, world_id):
            if self.fail:
                raise ConnectionError("graph read failed")
            return super().get(world_id)

    graph = InMemoryGraphRepository()
    builder, graph, search, _cache = _make(tmp_path, graph=graph)
    builder.build("w", inputs=None)
    before = sorted((n.label, n.id) for n in graph._nodes.values())
    cache = _Unreadable(WorldLoader(graph))
    cache.fail = True
    builder._cache = cache  # the same builder, reading through a failing cache

    report = builder.build("w", inputs=None, replace=True)

    assert report.ok is False and report.replaced is False
    assert [(w.stage, w.severity) for w in report.errors] == [("carry-over", "error")]
    assert "not replaced" in report.errors[0].message
    assert sorted((n.label, n.id) for n in graph._nodes.values()) == before
