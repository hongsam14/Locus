"""U9 services tests — persist_graph, orchestrator, editor, exporter (mocked)."""

from __future__ import annotations

from locus.shared.models import (
    ConnectionEdge,
    ConnectionKind,
    Entity,
    EntityType,
    IngestionResult,
    Knowledge,
    KnowledgeGraph,
    Provenance,
    Region,
    RegionLevel,
    RegionTopology,
    ScopeLink,
    ScopeType,
    SourceKind,
)
from locus.shared.storage.persistence import persist_graph
from locus.world import Editors, WorldBuilder, WorldFileExporter
from locus.world.build import BuildProviders
from locus.world.ontology.builder import OntologyBuild
from locus.world.topology.builder import TopologyBuild
from tests.shared.snapshots import snapshot_of


def _prov(src: SourceKind = SourceKind.INPUT) -> Provenance:
    return Provenance(source=src)


class _GraphRepo:
    def __init__(self) -> None:
        self.nodes: list = []
        self.edges: list = []
        self.deleted: list = []

    def upsert_nodes(self, nodes):
        self.nodes.extend(nodes)

    def upsert_edges(self, edges):
        self.edges.extend(edges)

    def delete_node(self, world_id, node_id):
        self.deleted.append(node_id)

    def find_nodes(self, world_id, label, filters=None):
        return [
            n
            for n in self.nodes
            if n.label == label
            and all(n.properties.get(k) == v for k, v in (filters or {}).items())
        ]

    def get_node(self, world_id, node_id):
        return next((n for n in self.nodes if n.id == node_id and n.world_id == world_id), None)

    def list_world_ids(self):
        return sorted({n.world_id for n in self.nodes})

    def delete_world(self, world_id):
        self.nodes = [n for n in self.nodes if n.world_id != world_id]


class _SearchRepo:
    def __init__(self) -> None:
        self.docs: list = []

    def index(self, docs):
        self.docs.extend(docs)

    def delete_world(self, world_id):
        self.docs = [d for d in self.docs if d.world_id != world_id]


class _NoCache:
    def __init__(self) -> None:
        self.invalidated: list[str] = []

    def get(self, world_id):  # pragma: no cover - builder never reads
        raise AssertionError("builder must not read the cache")

    def invalidate(self, world_id):
        self.invalidated.append(world_id)


def _builder(
    g, s, *, topology_factory, ontology_factory, wiki_factory=None, distiller=None, linker=None
):
    return WorldBuilder(
        g,
        s,
        _NoCache(),
        providers=BuildProviders(),
        ingestion_factory=lambda llm, vlm: _Ingest(),
        topology_factory=topology_factory,
        ontology_factory=lambda llm, emb, wiki: ontology_factory(wiki),
        wiki_factory=(lambda wid, llm, emb: wiki_factory(wid)) if wiki_factory else None,
        distiller_factory=(lambda llm: distiller) if distiller else None,
        linker_factory=(lambda llm, emb: linker) if linker else None,
    )


# --------------------------------------------------------------------------- #
# persist_graph
# --------------------------------------------------------------------------- #
def test_persist_graph_writes_nodes_edges_docs() -> None:
    g, s = _GraphRepo(), _SearchRepo()
    a = Region(world_id="w", name="A", level=RegionLevel.TOWN, provenance=_prov())
    k = Knowledge(world_id="w", statement="fact", title="fact", provenance=_prov())
    conn = ConnectionEdge(
        world_id="w",
        source_region_id=a.id,
        target_region_id=a.id,
        kind=ConnectionKind.ROUTE,
        weight=0.6,
        provenance=_prov(),
    )
    scope = ScopeLink(
        world_id="w", knowledge_id=k.id, region_id=a.id, scope_type=ScopeType.DIRECT, confidence=0.9
    )
    persist_graph(g, s, None, "w", regions=[a], knowledge=[k], connections=[conn], scopes=[scope])
    labels = {n.label for n in g.nodes}
    assert {"Region", "Knowledge"} <= labels
    assert any(e.type == "CONNECTED_TO" for e in g.edges)
    assert any(e.type == "SCOPED_TO" for e in g.edges)
    assert any(d.label == "Knowledge" for d in s.docs)


# --------------------------------------------------------------------------- #
# WorldBuilder
# --------------------------------------------------------------------------- #
class _Ingest:
    def ingest_all(self, world_id, inputs):
        return IngestionResult(
            world_id=world_id,
            entities=[
                Entity(
                    world_id=world_id, name="E", entity_type=EntityType.PLACE, provenance=_prov()
                )
            ],
            knowledge=[Knowledge(world_id=world_id, statement="k", title="k", provenance=_prov())],
        )


class _Topo:
    def build(self, ingestion, *, world_id):
        return TopologyBuild(
            RegionTopology(
                world_id=world_id,
                regions=[
                    Region(world_id=world_id, name="R", level=RegionLevel.TOWN, provenance=_prov())
                ],
            )
        )


class _Onto:
    def build(self, ingestion, topology, *, world_id):
        corr = Knowledge(
            world_id=world_id,
            statement="hot basin",
            title="hot basin",
            provenance=_prov(SourceKind.INFERRED),
        )
        return OntologyBuild(
            KnowledgeGraph(
                world_id=world_id,
                entities=ingestion.entities,
                knowledge=ingestion.knowledge + [corr],
            )
        )


def test_orchestrator_build_world_counts() -> None:
    g, s = _GraphRepo(), _SearchRepo()
    orch = _builder(
        g, s, topology_factory=lambda wiki: _Topo(), ontology_factory=lambda wiki: _Onto()
    )
    report = orch.build("w", inputs=None)
    assert report.world_id == "w"
    assert report.regions_created == 1
    assert report.entities_created == 1
    assert report.knowledge_created == 2
    assert report.corroborations_created == 1  # one inferred-wiki item
    assert {"Region", "Entity", "Knowledge"} <= {n.label for n in g.nodes}


class _StubDistiller:
    def distill(self, ingestion, topology, *, world_id):
        from locus.shared.models import PriorType, WikiDomain, WikiPrior

        return [
            WikiPrior(
                world_id=world_id,
                prior_type=PriorType.FACT,
                condition="river",
                effect="trade",
                domains=[WikiDomain.GEOGRAPHY],
                provenance=_prov(SourceKind.INFERRED),
            )
        ]


class _StubLinker:
    def link(self, priors, *, world_id):
        from locus.shared.models import WikiPriorLink

        if len(priors) < 1:
            return []
        return [
            WikiPriorLink(
                world_id=world_id,
                source_id=priors[0].id,
                target_id=priors[0].id,
                relation="self",
                weight=0.9,
                provenance=_prov(SourceKind.INFERRED),
            )
        ]


class _RecordingTopo:
    """Records the wiki it was constructed with and the build order (FR-H7)."""

    def __init__(self, log: list, wiki) -> None:
        self._log = log
        log.append(("topo.wiki", wiki))

    def build(self, ingestion, *, world_id):
        self._log.append(("topo.build", None))
        return TopologyBuild(
            RegionTopology(
                world_id=world_id,
                regions=[
                    Region(world_id=world_id, name="R", level=RegionLevel.TOWN, provenance=_prov())
                ],
            )
        )


class _RecordingOnto:
    def __init__(self, log: list, wiki) -> None:
        self._log = log
        log.append(("onto.wiki", wiki))

    def build(self, ingestion, topology, *, world_id):
        self._log.append(("onto.build", None))
        return OntologyBuild(KnowledgeGraph(world_id=world_id, entities=[], knowledge=[]))


def test_world_builder_passes_world_wiki_to_fresh_builders() -> None:
    """FR-H7 / BR-H2-2 + RE A12: each build constructs fresh builders with this
    world's wiki, so topology sees the wiki before it builds and no state is
    shared between builds."""
    g, s = _GraphRepo(), _SearchRepo()
    log: list = []
    wikis: dict[str, object] = {}

    def wiki_factory(world_id: str):
        wikis[world_id] = object()
        return wikis[world_id]

    orch = _builder(
        g,
        s,
        topology_factory=lambda wiki: _RecordingTopo(log, wiki),
        ontology_factory=lambda wiki: _RecordingOnto(log, wiki),
        wiki_factory=wiki_factory,
    )
    orch.build("w", inputs=None)
    orch.build("w2", inputs=None)
    events = [e for e, _ in log]
    assert events.index("topo.wiki") < events.index("topo.build")
    assert events.index("onto.wiki") < events.index("onto.build")
    # each build got its own world's wiki object
    topo_wikis = [w for e, w in log if e == "topo.wiki"]
    assert topo_wikis == [wikis["w"], wikis["w2"]]


def test_world_builder_without_wiki_factory_passes_none() -> None:
    """No wiki factory -> builders get ``None`` (existing no-LLM guard preserved)."""
    g, s = _GraphRepo(), _SearchRepo()
    log: list = []
    orch = _builder(
        g,
        s,
        topology_factory=lambda wiki: _RecordingTopo(log, wiki),
        ontology_factory=lambda wiki: _RecordingOnto(log, wiki),
    )
    orch.build("w", inputs=None)
    # both builders are constructed (with wiki=None) before anything is built
    assert [e for e, _ in log] == ["topo.wiki", "onto.wiki", "topo.build", "onto.build"]
    assert all(w is None for e, w in log if e.endswith(".wiki"))


def test_orchestrator_distills_priors_and_links_per_world() -> None:
    g, s = _GraphRepo(), _SearchRepo()
    orch = _builder(
        g,
        s,
        topology_factory=lambda wiki: _Topo(),
        ontology_factory=lambda wiki: _Onto(),
        distiller=_StubDistiller(),
        linker=_StubLinker(),
    )
    orch.build("w", inputs=None)
    # this world's own WikiPrior node + PRIOR_RELATED_TO edge persisted (BR-A12)
    assert any(n.label == "WikiPrior" and n.world_id == "w" for n in g.nodes)
    assert any(e.type == "PRIOR_RELATED_TO" for e in g.edges)


# --------------------------------------------------------------------------- #
# Editors (U3: was WorldEditor)
# --------------------------------------------------------------------------- #
def test_graph_editor_upsert_and_delete() -> None:
    # U3 intended change: BR-U3-1, 이탈 1 — a replace write; deletes go by kind
    from locus.knowledge.cache import WorldCache
    from locus.knowledge.loader import WorldLoader
    from locus.shared.models import WorldMeta
    from locus.shared.storage.persistence import persist_graph
    from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository

    g, s = InMemoryGraphRepository(), InMemorySearchRepository()
    # U8 intended change: U3 review S21 — the world must exist and the editors read it
    persist_graph(g, s, None, "w", meta=WorldMeta(id="w", name="W"))
    editors = Editors.assemble(g, s, cache=WorldCache(WorldLoader(g)))
    k = Knowledge(world_id="w", statement="new fact", title="new fact", provenance=_prov())
    editors.knowledge.upsert_knowledge(k)
    assert g.get_node("w", k.id).label == "Knowledge"  # type: ignore[union-attr]
    assert ("w", k.id) in s.docs
    editors.knowledge.delete_knowledge("w", k.id)
    assert g.get_node("w", k.id) is None and ("w", k.id) not in s.docs


# --------------------------------------------------------------------------- #
# WorldFileExporter
# --------------------------------------------------------------------------- #
class _Loader:
    def get(self, world_id):
        kg = KnowledgeGraph(
            world_id=world_id,
            knowledge=[Knowledge(world_id=world_id, statement="x", title="x", provenance=_prov())],
        )
        topo = RegionTopology(
            world_id=world_id,
            regions=[
                Region(world_id=world_id, name="R", level=RegionLevel.TOWN, provenance=_prov())
            ],
        )
        return snapshot_of(kg, topo)


def test_exporter_serializes_world() -> None:
    data = WorldFileExporter(_Loader()).export_world("w")
    assert data["world_id"] == "w"
    assert len(data["regions"]) == 1 and len(data["knowledge"]) == 1
    assert data["regions"][0]["name"] == "R"


# --------------------------------------------------------------------------- #
# U2 Step 11 — editor writes invalidate the cache and touch WorldMeta (BR-U2-17/23, EX-23)
# --------------------------------------------------------------------------- #
def test_editor_writes_invalidate_cache_and_touch_meta() -> None:
    from locus.knowledge.cache import WorldCache
    from locus.knowledge.loader import WorldLoader
    from locus.shared.models import WorldMeta
    from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository

    graph, search = InMemoryGraphRepository(), InMemorySearchRepository()
    cache = WorldCache(WorldLoader(graph))
    region = Region(world_id="w", name="R", level=RegionLevel.TOWN, provenance=_prov())
    persist_graph(graph, search, None, "w", regions=[region], meta=WorldMeta(id="w", name="W"))
    before = cache.get("w").meta
    assert before is not None and before.last_writer == "build"

    editors = Editors.assemble(graph, search, cache=cache)
    gen = cache.generation("w")
    editors.regions.upsert_region(region.model_copy(update={"description": "edited"}))
    assert cache.generation("w") == gen + 1 and not cache.is_cached("w")
    after = cache.get("w").meta
    assert (
        after is not None and after.last_writer == "edit" and after.updated_at >= before.updated_at
    )
    assert cache.get("w").regions_by_id[region.id].description == "edited"

    k = Knowledge(world_id="w", statement="s", title="t", provenance=_prov())
    editors.knowledge.upsert_knowledge(k)
    editors.knowledge.delete_knowledge("w", k.id)
    assert cache.generation("w") == gen + 3


def test_editor_does_not_create_meta_for_pre_u2_worlds() -> None:
    from locus.knowledge.cache import WorldCache
    from locus.knowledge.loader import WorldLoader
    from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository

    graph, search = InMemoryGraphRepository(), InMemorySearchRepository()
    cache = WorldCache(WorldLoader(graph))
    region = Region(world_id="old", name="R", level=RegionLevel.TOWN, provenance=_prov())
    persist_graph(graph, search, None, "old", regions=[region])  # no meta
    Editors.assemble(graph, search, cache=cache).regions.upsert_region(region)
    assert graph.find_nodes("old", "WorldMeta") == [] and cache.get("old").meta is None


def test_deleting_a_region_cascades_to_its_npcs() -> None:  # review #8
    from locus.knowledge.cache import WorldCache
    from locus.knowledge.loader import WorldLoader
    from locus.shared.models import NPC
    from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository

    graph, search = InMemoryGraphRepository(), InMemorySearchRepository()
    cache = WorldCache(WorldLoader(graph))
    keep = Region(world_id="w", name="Keep", level=RegionLevel.TOWN, provenance=_prov())
    gone = Region(world_id="w", name="Gone", level=RegionLevel.TOWN, provenance=_prov())
    npcs = [
        NPC(
            world_id="w",
            name="A",
            role="r",
            description="d",
            home_region_id=gone.id,
            provenance=_prov(),
        ),
        NPC(
            world_id="w",
            name="B",
            role="r",
            description="d",
            home_region_id=keep.id,
            provenance=_prov(),
        ),
    ]
    persist_graph(graph, search, None, "w", regions=[keep, gone], npcs=npcs)
    # U3 intended change: BR-U3-8 — the region delete reports what it removed
    report = Editors.assemble(graph, search, cache=cache).regions.delete_region("w", gone.id)
    assert set(report.deleted_ids) == {gone.id, npcs[0].id}
    snap = cache.get("w")
    assert [n.name for n in snap.npcs] == ["B"] and snap.load_warnings == []


def test_editor_invalidates_even_when_indexing_fails() -> None:  # review #12
    import pytest

    from locus.knowledge.cache import WorldCache
    from locus.knowledge.loader import WorldLoader
    from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository

    graph, search = InMemoryGraphRepository(), InMemorySearchRepository()
    cache = WorldCache(WorldLoader(graph))
    region = Region(world_id="w", name="R", level=RegionLevel.TOWN, provenance=_prov())
    persist_graph(graph, search, None, "w", regions=[region])
    cache.get("w")
    search.fail_on_index = RuntimeError("opensearch down")
    k = Knowledge(world_id="w", statement="s", title="t", provenance=_prov())
    with pytest.raises(RuntimeError):
        Editors.assemble(graph, search, cache=cache).knowledge.upsert_knowledge(k)
    assert not cache.is_cached("w") and len(cache.get("w").kg.knowledge) == 1
