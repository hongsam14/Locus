"""U6 Wiki build tests — graph_mapping, distiller, builder, admin, bundled (mocked)."""

from __future__ import annotations

from locus import REALWORLD_WORLD_ID
from locus.commonsense_wiki import WikiAdmin, WikiBuilder, load_bundled_realworld
from locus.commonsense_wiki.distiller import PriorDistiller
from locus.commonsense_wiki.schemas import PriorBatch, PriorSuggestion
from locus.models import (
    ConnectionEdge,
    ConnectionKind,
    Entity,
    EntityType,
    IngestionResult,
    Knowledge,
    PriorType,
    Provenance,
    Region,
    RegionLevel,
    RegionTopology,
    ScopeLink,
    SourceKind,
    WikiPrior,
)
from locus.storage import graph_mapping as gm


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


# --------------------------------------------------------------------------- #
# graph_mapping (pure)
# --------------------------------------------------------------------------- #
def test_region_node_flattens_provenance_and_attributes() -> None:
    r = Region(
        world_id="w",
        name="T",
        level=RegionLevel.TOWN,
        attributes={"terrain": "river"},
        provenance=_prov(),
    )
    node = gm.region_to_node(r)
    assert node.label == "Region"
    assert node.properties["prov_source"] == "input"
    # nested dict attributes are JSON-encoded (Neo4j-safe)
    assert isinstance(node.properties["attributes"], str)
    assert "provenance" not in node.properties


def test_contains_and_scope_edges() -> None:
    parent = Region(world_id="w", name="P", level=RegionLevel.PROVINCE, provenance=_prov())
    child = Region(
        world_id="w", name="C", level=RegionLevel.TOWN, parent_id=parent.id, provenance=_prov()
    )
    edges = gm.contains_edges([parent, child])
    assert edges[0].type == "CONTAINS"
    assert edges[0].source_id == parent.id and edges[0].target_id == child.id

    s = ScopeLink(world_id="w", knowledge_id="k1", region_id=child.id, confidence=0.9)
    se = gm.scope_edges([s])[0]
    assert se.type == "SCOPED_TO" and se.properties["confidence"] == 0.9


def test_wikiprior_doc_carries_meta() -> None:
    p = WikiPrior(
        prior_type=PriorType.TERRAIN_RULE, condition="mountain", effect="slow", provenance=_prov()
    )
    doc = gm.wikiprior_doc(p, REALWORLD_WORLD_ID)
    assert doc.label == "WikiPrior"
    assert doc.meta["condition"] == "mountain"
    assert doc.meta["effect"] == "slow"


def test_connection_edges_count() -> None:
    c = ConnectionEdge(
        world_id="w",
        source_region_id="a",
        target_region_id="b",
        kind=ConnectionKind.ROUTE,
        weight=0.6,
        provenance=_prov(),
    )
    assert gm.connection_edges([c])[0].properties["weight"] == 0.6


# --------------------------------------------------------------------------- #
# PriorDistiller
# --------------------------------------------------------------------------- #
class _FakeLLM:
    def __init__(self, batch: PriorBatch) -> None:
        self._batch = batch

    def structured(self, prompt, schema, *, system=None):
        return self._batch


def test_distiller_builds_wikipriors() -> None:
    batch = PriorBatch(
        items=[
            PriorSuggestion(
                prior_type=PriorType.TERRAIN_RULE,
                condition="mountain",
                effect="slow",
                confidence=0.9,
            ),
            PriorSuggestion(condition="", effect="x"),  # invalid -> dropped (BR-U6-4)
        ]
    )
    ingestion = IngestionResult(world_id=REALWORLD_WORLD_ID)
    topo = RegionTopology(world_id=REALWORLD_WORLD_ID)
    priors = PriorDistiller(_FakeLLM(batch)).distill(ingestion, topo, world_id=REALWORLD_WORLD_ID)
    assert len(priors) == 1
    assert priors[0].provenance.source == SourceKind.INFERRED_WIKI


def test_distiller_graceful_on_error() -> None:
    class _Boom:
        def structured(self, *a, **k):
            raise RuntimeError("x")

    assert (
        PriorDistiller(_Boom()).distill(
            IngestionResult(world_id="__realworld__"),
            RegionTopology(world_id="__realworld__"),
            world_id="__realworld__",
        )
        == []
    )


# --------------------------------------------------------------------------- #
# WikiBuilder (mock pipeline + repos)
# --------------------------------------------------------------------------- #
class _FakeIngestion:
    def ingest_all(self, world_id, inputs):
        return IngestionResult(
            world_id=world_id,
            entities=[
                Entity(
                    world_id=world_id, name="Mt", entity_type=EntityType.TERRAIN, provenance=_prov()
                )
            ],
            knowledge=[
                Knowledge(world_id=world_id, statement="rivers enable trade", provenance=_prov())
            ],
        )


class _FakeTopology:
    def build(self, ingestion, *, world_id):
        return RegionTopology(
            world_id=world_id,
            regions=[
                Region(
                    world_id=world_id, name="Vale", level=RegionLevel.PROVINCE, provenance=_prov()
                )
            ],
        )


class _FakeOntology:
    def build(self, ingestion, topology, *, world_id):
        from locus.models import KnowledgeGraph

        return KnowledgeGraph(
            world_id=world_id, entities=ingestion.entities, knowledge=ingestion.knowledge
        )


class _RecordingGraphRepo:
    def __init__(self) -> None:
        self.nodes: list = []
        self.edges: list = []

    def upsert_nodes(self, nodes):
        self.nodes.extend(nodes)

    def upsert_edges(self, edges):
        self.edges.extend(edges)

    def find_nodes(self, world_id, label, filters=None):
        return [n for n in self.nodes if n.label == label]


class _RecordingSearchRepo:
    def __init__(self) -> None:
        self.docs: list = []

    def index(self, docs):
        self.docs.extend(docs)


def test_wiki_builder_persists_twin_and_priors() -> None:
    graph, search = _RecordingGraphRepo(), _RecordingSearchRepo()
    distiller = PriorDistiller(
        _FakeLLM(
            PriorBatch(items=[PriorSuggestion(condition="mountain", effect="slow", confidence=0.8)])
        )
    )
    builder = WikiBuilder(
        _FakeIngestion(), _FakeTopology(), _FakeOntology(), distiller, graph, search, embedding=None
    )
    report = builder.build_wiki(load_bundled_realworld())

    assert report.world_id == REALWORLD_WORLD_ID
    assert report.regions == 1 and report.entities == 1 and report.knowledge == 1
    assert report.priors == 1
    # nodes persisted include a WikiPrior + Region + Entity + Knowledge
    labels = {n.label for n in graph.nodes}
    assert {"Region", "Entity", "Knowledge", "WikiPrior"} <= labels
    # search docs indexed (knowledge + entity + wikiprior)
    assert any(d.label == "WikiPrior" for d in search.docs)


# --------------------------------------------------------------------------- #
# WikiAdmin
# --------------------------------------------------------------------------- #
def test_wiki_admin_upsert_prior() -> None:
    graph, search = _RecordingGraphRepo(), _RecordingSearchRepo()
    admin = WikiAdmin(graph, search, embedding=None)
    p = WikiPrior(
        prior_type=PriorType.FACT, condition="sea", effect="isolation", provenance=_prov()
    )
    admin.upsert_prior(p)
    assert graph.nodes[0].label == "WikiPrior"
    assert search.docs[0].id == p.id
    assert len(admin.list_priors()) == 1


# --------------------------------------------------------------------------- #
# bundled
# --------------------------------------------------------------------------- #
def test_bundled_realworld_inputs() -> None:
    inputs = load_bundled_realworld()
    assert inputs.memos and inputs.structured_maps
    assert inputs.structured_maps[0]["regions"]
