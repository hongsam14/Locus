"""U9 services tests — persist_graph, orchestrator, editor, exporter (mocked)."""

from __future__ import annotations

from locus.models import (
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
from locus.services import Exporter, GraphEditor, PipelineOrchestrator
from locus.storage.persistence import persist_graph


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
        return [n for n in self.nodes if n.label == label]


class _SearchRepo:
    def __init__(self) -> None:
        self.docs: list = []

    def index(self, docs):
        self.docs.extend(docs)


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
# PipelineOrchestrator
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
        return RegionTopology(
            world_id=world_id,
            regions=[
                Region(world_id=world_id, name="R", level=RegionLevel.TOWN, provenance=_prov())
            ],
        )


class _Onto:
    def build(self, ingestion, topology, *, world_id):
        corr = Knowledge(
            world_id=world_id,
            statement="hot basin",
            title="hot basin",
            provenance=_prov(SourceKind.INFERRED_WIKI),
        )
        return KnowledgeGraph(
            world_id=world_id,
            entities=ingestion.entities,
            knowledge=ingestion.knowledge + [corr],
        )


def test_orchestrator_build_world_counts() -> None:
    g, s = _GraphRepo(), _SearchRepo()
    orch = PipelineOrchestrator(_Ingest(), _Topo(), _Onto(), g, s, embedding=None)
    report = orch.build_world("w", inputs=None)
    assert report.world_id == "w"
    assert report.regions_created == 1
    assert report.entities_created == 1
    assert report.knowledge_created == 2
    assert report.corroborations_created == 1  # one inferred-wiki item
    assert {"Region", "Entity", "Knowledge"} <= {n.label for n in g.nodes}


class _StubDistiller:
    def distill(self, ingestion, topology, *, world_id):
        from locus.models import PriorType, WikiDomain, WikiPrior

        return [
            WikiPrior(
                world_id=world_id,
                prior_type=PriorType.FACT,
                condition="river",
                effect="trade",
                domains=[WikiDomain.GEOGRAPHY],
                provenance=_prov(SourceKind.INFERRED_WIKI),
            )
        ]


class _StubLinker:
    def link(self, priors, *, world_id):
        from locus.models import WikiPriorLink

        if len(priors) < 1:
            return []
        return [
            WikiPriorLink(
                world_id=world_id,
                source_id=priors[0].id,
                target_id=priors[0].id,
                relation="self",
                weight=0.9,
                provenance=_prov(SourceKind.INFERRED_WIKI),
            )
        ]


class _OrderTopo:
    """Records the order of set_wiki vs build calls (FR-H7)."""

    def __init__(self, log: list) -> None:
        self._log = log

    def set_wiki(self, wiki) -> None:
        self._log.append("topo.set_wiki")

    def build(self, ingestion, *, world_id):
        self._log.append("topo.build")
        return RegionTopology(
            world_id=world_id,
            regions=[
                Region(world_id=world_id, name="R", level=RegionLevel.TOWN, provenance=_prov())
            ],
        )


class _OrderOnto:
    def __init__(self, log: list) -> None:
        self._log = log

    def set_wiki(self, wiki) -> None:
        self._log.append("onto.set_wiki")

    def build(self, ingestion, topology, *, world_id):
        self._log.append("onto.build")
        return KnowledgeGraph(world_id=world_id, entities=[], knowledge=[])


def test_orchestrator_injects_wiki_before_topology_build() -> None:
    """FR-H7 / BR-H2-2: topology.set_wiki must run BEFORE topology.build so the
    topology can reflect this world's persisted priors."""
    g, s = _GraphRepo(), _SearchRepo()
    log: list = []
    orch = PipelineOrchestrator(
        _Ingest(), _OrderTopo(log), _OrderOnto(log), g, s, embedding=None, llm=object()
    )
    orch.build_world("w", inputs=None)
    assert log.index("topo.set_wiki") < log.index("topo.build")
    assert log.index("onto.set_wiki") < log.index("onto.build")


def test_orchestrator_skips_wiki_when_no_llm() -> None:
    """No LLM -> no wiki injection (existing guard preserved)."""
    g, s = _GraphRepo(), _SearchRepo()
    log: list = []
    orch = PipelineOrchestrator(
        _Ingest(), _OrderTopo(log), _OrderOnto(log), g, s, embedding=None, llm=None
    )
    orch.build_world("w", inputs=None)
    assert "topo.set_wiki" not in log and "onto.set_wiki" not in log
    assert log == ["topo.build", "onto.build"]


def test_orchestrator_distills_priors_and_links_per_world() -> None:
    g, s = _GraphRepo(), _SearchRepo()
    orch = PipelineOrchestrator(
        _Ingest(),
        _Topo(),
        _Onto(),
        g,
        s,
        embedding=None,
        distiller=_StubDistiller(),
        linker=_StubLinker(),
    )
    orch.build_world("w", inputs=None)
    # this world's own WikiPrior node + PRIOR_RELATED_TO edge persisted (BR-A12)
    assert any(n.label == "WikiPrior" and n.world_id == "w" for n in g.nodes)
    assert any(e.type == "PRIOR_RELATED_TO" for e in g.edges)


# --------------------------------------------------------------------------- #
# GraphEditor
# --------------------------------------------------------------------------- #
def test_graph_editor_upsert_and_delete() -> None:
    g, s = _GraphRepo(), _SearchRepo()
    editor = GraphEditor(g, s, embedding=None)
    k = Knowledge(world_id="w", statement="new fact", title="new fact", provenance=_prov())
    editor.upsert_knowledge(k)
    assert g.nodes[0].label == "Knowledge"
    assert s.docs and s.docs[0].id == k.id
    editor.delete_node("w", "n1")
    assert g.deleted == ["n1"]


# --------------------------------------------------------------------------- #
# Exporter
# --------------------------------------------------------------------------- #
class _Loader:
    def load(self, world_id):
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
        return kg, topo


def test_exporter_serializes_world() -> None:
    data = Exporter(_Loader()).export_world("w")
    assert data["world_id"] == "w"
    assert len(data["regions"]) == 1 and len(data["knowledge"]) == 1
    assert data["regions"][0]["name"] == "R"
