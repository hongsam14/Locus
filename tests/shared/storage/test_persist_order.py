"""V7 — ``persist_graph`` writes the world's version mark last (TP-V7-6, BR-V7-06)."""

from __future__ import annotations

from locus.shared.models import (
    Knowledge,
    Provenance,
    Region,
    RegionLevel,
    ScopeLink,
    ScopeType,
    SourceKind,
    WorldMeta,
)
from locus.shared.storage.persistence import persist_graph
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository

_PROV = Provenance(source=SourceKind.INPUT)


class _Graph(InMemoryGraphRepository):
    def __init__(self, log: list, *, fail_edges: bool = False, fail_meta: bool = False) -> None:
        super().__init__()
        self.log, self.fail_edges, self.fail_meta = log, fail_edges, fail_meta

    def upsert_nodes(self, nodes) -> None:
        labels = sorted({n.label for n in nodes})
        if self.fail_meta and labels == ["WorldMeta"]:
            raise RuntimeError("meta write failed")
        self.log.append(("nodes", labels))
        super().upsert_nodes(nodes)

    def upsert_edges(self, edges) -> None:
        if self.fail_edges:
            raise RuntimeError("edge write failed")
        self.log.append(("edges",))
        super().upsert_edges(edges)


class _Search(InMemorySearchRepository):
    def __init__(self, log: list, *, fail: bool = False) -> None:
        super().__init__()
        self.log, self.fail = log, fail

    def index(self, docs) -> None:
        if self.fail:
            raise RuntimeError("index failed")
        self.log.append(("index",))
        super().index(docs)


def _persist(graph, search):
    region = Region(id="a", world_id="w", name="A", level=RegionLevel.TOWN, provenance=_PROV)
    k = Knowledge(id="k", world_id="w", statement="s", title="t", provenance=_PROV)
    return persist_graph(
        graph,
        search,
        None,
        "w",
        regions=[region],
        knowledge=[k],
        scopes=[
            ScopeLink(world_id="w", knowledge_id="k", region_id="a", scope_type=ScopeType.DIRECT)
        ],
        meta=WorldMeta(id="w", name="w"),
    )


def test_tp_v7_6_the_mark_goes_in_after_edges_and_index() -> None:
    log: list = []
    warnings = _persist(_Graph(log), _Search(log))
    assert not warnings
    assert log == [
        ("nodes", ["Knowledge", "Region"]),
        ("edges",),
        ("index",),
        ("nodes", ["WorldMeta"]),
    ]


def test_tp_v7_6_a_failed_edge_write_leaves_no_mark() -> None:
    log: list = []
    graph = _Graph(log, fail_edges=True)
    warnings = _persist(graph, _Search(log))
    assert [w.stage for w in warnings] == ["persist-graph"] and warnings[0].severity == "error"
    assert ("nodes", ["WorldMeta"]) not in log and not graph.find_nodes("w", "WorldMeta")


def test_tp_v7_6_a_failed_index_still_writes_the_mark() -> None:
    log: list = []
    graph = _Graph(log)
    warnings = _persist(graph, _Search(log, fail=True))
    assert [(w.stage, w.severity) for w in warnings] == [("persist-search", "error")]
    assert log[-1] == ("nodes", ["WorldMeta"]) and graph.find_nodes("w", "WorldMeta")


def test_tp_v7_6_a_failed_mark_write_is_an_error() -> None:
    log: list = []
    warnings = _persist(_Graph(log, fail_meta=True), _Search(log))
    assert [(w.stage, w.severity) for w in warnings] == [("persist-meta", "error")]
