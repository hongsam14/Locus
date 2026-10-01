"""U1 storage tests — Cypher/query construction (mocked driver/client)."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from locus.shared.storage import Neo4jGraphRepository, Node, build_search_body, index_mapping
from locus.shared.storage.neo4j_repo import _safe_ident


# --------------------------------------------------------------------------- #
# Fake Neo4j driver
# --------------------------------------------------------------------------- #
class _FakeSession:
    def __init__(self, recorder: list[tuple[str, dict]], rows: list[dict]) -> None:
        self._recorder = recorder
        self._rows = rows

    def run(self, query: str, **params):
        self._recorder.append((query, params))
        return [_FakeRecord(r) for r in self._rows]


class _FakeRecord:
    def __init__(self, data: dict) -> None:
        self._data = data

    def data(self) -> dict:
        return self._data


def _repo_with_fake_driver(rows: list[dict] | None = None):
    recorder: list[tuple[str, dict]] = []
    repo = Neo4jGraphRepository(uri="bolt://x", user="u", password="p")

    driver = MagicMock()

    @contextmanager
    def _session():
        yield _FakeSession(recorder, rows or [])

    driver.session.side_effect = _session
    repo._driver = driver
    return repo, recorder


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_safe_ident_rejects_injection() -> None:
    with pytest.raises(ValueError):
        _safe_ident("Region) DETACH DELETE n //")
    assert _safe_ident("Region") == "Region"


def test_not_connected_raises() -> None:
    repo = Neo4jGraphRepository(uri="bolt://x", user="u", password="p")
    with pytest.raises(RuntimeError, match="not connected"):
        repo.get_node("w1", "n1")


def test_upsert_nodes_builds_merge_cypher() -> None:
    repo, recorder = _repo_with_fake_driver()
    repo.upsert_nodes([Node(id="r1", label="Region", world_id="w1", properties={"name": "Town"})])
    query, params = recorder[0]
    assert "MERGE (n:Region {id: $id, world_id: $world_id})" in query
    assert params == {"id": "r1", "world_id": "w1", "props": {"name": "Town"}}


def test_get_node_scopes_by_world_id() -> None:
    rows = [{"labels": ["Region"], "props": {"id": "r1", "name": "Town"}}]
    repo, recorder = _repo_with_fake_driver(rows)
    node = repo.get_node("w1", "r1")
    assert node is not None
    assert node.label == "Region"
    assert node.id == "r1"
    _, params = recorder[0]
    assert params["world_id"] == "w1"


def test_ensure_schema_creates_constraints() -> None:
    repo, recorder = _repo_with_fake_driver()
    repo.ensure_schema()
    queries = " ".join(q for q, _ in recorder)
    assert "CREATE CONSTRAINT" in queries
    assert "FOR (n:Region) REQUIRE n.id IS UNIQUE" in queries
    assert "FOR (n:WikiPrior) REQUIRE n.id IS UNIQUE" in queries
    # World nodes are no longer persisted (CL-A1=A)
    assert "(n:World)" not in queries  # WorldMeta is a different label (U2)


def test_build_search_body_has_world_filter() -> None:
    body = build_search_body("w1", "mountain", [0.1, 0.2], k=3, filters={"label": "Knowledge"})
    filters = body["query"]["bool"]["filter"]
    assert {"term": {"world_id": "w1"}} in filters
    assert {"term": {"label": "Knowledge"}} in filters
    shoulds = body["query"]["bool"]["should"]
    assert any("knn" in s for s in shoulds)
    assert any("match" in s for s in shoulds)


def test_build_search_body_without_embedding_is_bm25_only() -> None:
    body = build_search_body("w1", "river", None, k=5, filters=None)
    shoulds = body["query"]["bool"]["should"]
    assert all("knn" not in s for s in shoulds)


def test_index_mapping_dimension_and_knn() -> None:
    mapping = index_mapping(1536)
    emb = mapping["mappings"]["properties"]["embedding"]
    assert emb["type"] == "knn_vector"
    assert emb["dimension"] == 1536
    assert mapping["settings"]["index"]["knn"] is True


# --------------------------------------------------------------------------- #
# U2 Step 3 — NPC / WorldMeta / relation mapping, persist_graph extensions, fakes
# --------------------------------------------------------------------------- #
from locus.shared.models import (  # noqa: E402
    NPC,
    BuildWarning,
    Provenance,
    Relation,
    SourceKind,
    WorldMeta,
)
from locus.shared.storage import ConstraintViolation  # noqa: E402
from locus.shared.storage import graph_mapping as gm  # noqa: E402
from locus.shared.storage.persistence import persist_graph  # noqa: E402
from tests.shared.storage.fakes import (  # noqa: E402
    InMemoryGraphRepository,
    InMemorySearchRepository,
)


def _npc(world_id: str = "w", region: str = "r1") -> NPC:
    return NPC(
        world_id=world_id,
        name="Tomas",
        role="mayor",
        description="Governs Riverton.",
        home_region_id=region,
        traits=["stern"],
        provenance=Provenance(source=SourceKind.INPUT),
    )


def test_npc_and_worldmeta_node_roundtrip() -> None:
    npc = _npc()
    assert gm.node_to_npc(gm.npc_to_node(npc)) == npc
    meta = WorldMeta(id="w", name="World", description="d", last_writer="import")
    node = gm.worldmeta_to_node(meta)
    assert node.label == "WorldMeta" and node.world_id == "w" and node.properties["world_id"] == "w"
    assert gm.node_to_worldmeta(node) == meta
    assert gm.npc_doc(npc).label == "NPC" and "Tomas" in gm.npc_doc(npc).text


def test_relation_edge_roundtrip_keeps_id_and_provenance() -> None:
    rel = Relation(
        world_id="w",
        source_id="a",
        target_id="b",
        relation_type="rules",
        confidence=0.7,
        provenance=Provenance(source=SourceKind.INFERRED, generated_by="llm"),
    )
    [edge] = gm.relation_edges([rel])
    assert gm.edge_to_relation(edge) == rel


def test_persist_graph_writes_npcs_and_meta() -> None:
    graph, search = InMemoryGraphRepository(), InMemorySearchRepository()
    npc = _npc()
    warnings = persist_graph(graph, search, None, "w", npcs=[npc], meta=WorldMeta(id="w", name="W"))
    assert warnings == []
    assert [n.id for n in graph.find_nodes("w", "NPC")] == [npc.id]
    assert graph.find_nodes("w", "WorldMeta")[0].id == "w"
    assert [e.type for e in graph.get_edges("w", ["LIVES_IN"])] == ["LIVES_IN"]
    assert search.docs[("w", npc.id)].label == "NPC"
    graph.delete_world("w")
    search.delete_world("w")
    assert graph.list_world_ids() == [] and search.docs == {}  # EX-22 (fakes)


def test_persist_failures_are_errors_not_warnings() -> None:
    graph, search = InMemoryGraphRepository(), InMemorySearchRepository()
    graph.fail_on_upsert = RuntimeError("neo4j down")
    warnings = persist_graph(graph, search, None, "w", npcs=[_npc()])
    assert [w.stage for w in warnings] == ["persist-graph"] and warnings[0].severity == "error"
    assert search.docs == {}  # a failed graph write never reaches the search index (review #1)
    graph2, search2 = InMemoryGraphRepository(), InMemorySearchRepository()
    search2.fail_on_index = RuntimeError("opensearch down")
    warnings = persist_graph(graph2, search2, None, "w", npcs=[_npc()])
    assert [w.stage for w in warnings] == ["persist-search"] and warnings[0].severity == "error"


def test_id_collision_with_another_world_is_reported() -> None:
    graph, search = InMemoryGraphRepository(), InMemorySearchRepository()
    npc = _npc(world_id="a")
    assert persist_graph(graph, search, None, "a", npcs=[npc]) == []
    clash = npc.model_copy(update={"world_id": "b"})  # same id, other world (BR-U2-4)
    warnings = persist_graph(graph, search, None, "b", npcs=[clash])
    assert warnings and warnings[0].severity == "error" and "remap=true" in warnings[0].message
    with pytest.raises(ConstraintViolation):
        graph.upsert_nodes([gm.npc_to_node(clash)])


def test_delete_world_cypher_has_no_label_filter_and_list_world_ids() -> None:
    repo, recorder = _repo_with_fake_driver(rows=[{"world_id": "a"}, {"world_id": "b"}])
    repo.delete_world("w")
    query, params = recorder[-1]
    assert query.startswith("MATCH (n {world_id: $world_id}) DETACH DELETE n")  # no label filter
    assert params == {"world_id": "w"}
    assert repo.list_world_ids() == ["a", "b"]
    assert "DISTINCT n.world_id" in recorder[-1][0]


def test_ensure_schema_covers_npc_and_worldmeta() -> None:
    repo, recorder = _repo_with_fake_driver()
    repo.ensure_schema()
    joined = " ".join(q for q, _ in recorder)
    assert "(n:NPC)" in joined and "(n:WorldMeta)" in joined


def test_build_warning_default_severity_is_warning() -> None:
    assert BuildWarning(stage="embed", message="x").severity == "warning"


def test_edges_of_different_identity_coexist() -> None:  # review #4
    from locus.knowledge.loader import WorldLoader
    from locus.shared.models import (
        ConnectionEdge,
        ConnectionKind,
        Entity,
        EntityType,
        Region,
        RegionLevel,
    )

    prov = Provenance(source=SourceKind.INPUT)
    graph, search = InMemoryGraphRepository(), InMemorySearchRepository()
    a = Region(world_id="w", name="A", level=RegionLevel.TOWN, provenance=prov)
    b = Region(world_id="w", name="B", level=RegionLevel.TOWN, provenance=prov)
    e1 = Entity(world_id="w", name="E1", entity_type=EntityType.PERSON, provenance=prov)
    e2 = Entity(world_id="w", name="E2", entity_type=EntityType.PERSON, provenance=prov)
    rels = [
        Relation(
            world_id="w", source_id=e1.id, target_id=e2.id, relation_type="rules", provenance=prov
        ),
        Relation(
            world_id="w", source_id=e1.id, target_id=e2.id, relation_type="hates", provenance=prov
        ),
    ]
    conns = [
        ConnectionEdge(
            world_id="w",
            source_region_id=a.id,
            target_region_id=b.id,
            kind=ConnectionKind.ADJACENT,
            weight=0.9,
            provenance=prov,
        ),
        ConnectionEdge(
            world_id="w",
            source_region_id=a.id,
            target_region_id=b.id,
            kind=ConnectionKind.ROUTE,
            weight=0.2,
            provenance=prov,
        ),
    ]
    persist_graph(
        graph,
        search,
        None,
        "w",
        regions=[a, b],
        entities=[e1, e2],
        relations=rels,
        connections=conns,
    )
    snap = WorldLoader(graph).load("w")
    assert {r.relation_type for r in snap.kg.relations} == {"rules", "hates"}
    assert {str(c.kind) for c in snap.topo.connections} == {"adjacent", "route"}


def test_upsert_edges_cypher_merges_on_identity() -> None:
    from locus.shared.storage.base import Edge

    repo, recorder = _repo_with_fake_driver()
    repo.upsert_edges(
        [
            Edge(
                type="RELATED_TO",
                source_id="a",
                target_id="b",
                world_id="w",
                properties={"id": "r1"},
            ),
            Edge(
                type="CONNECTED_TO",
                source_id="a",
                target_id="b",
                world_id="w",
                properties={"kind": "route"},
            ),
            Edge(type="SCOPED_TO", source_id="k", target_id="r", world_id="w", properties={}),
        ]
    )
    queries = [q for q, _ in recorder]
    assert (
        "MERGE (a)-[r:RELATED_TO {id: $key}]->(b)" in queries[0] and recorder[0][1]["key"] == "r1"
    )
    assert "MERGE (a)-[r:CONNECTED_TO {kind: $key}]->(b)" in queries[1]
    assert "MERGE (a)-[r:SCOPED_TO]->(b)" in queries[2]


def test_opensearch_bulk_omits_empty_vectors_and_reports_errors() -> None:  # review #11
    from unittest.mock import MagicMock

    from locus.shared.models import SearchDoc
    from locus.shared.storage import OpenSearchRepository

    repo = OpenSearchRepository(url="http://x", index="i", vector_dimension=4)
    client = MagicMock()
    client.bulk.return_value = {"errors": False, "items": []}
    repo._client = client
    repo.index([SearchDoc(id="d", world_id="w", label="NPC", text="t")])
    body = client.bulk.call_args.kwargs["body"]
    assert "embedding" not in body[1]
    client.bulk.return_value = {"errors": True, "items": [{"index": {"error": {"reason": "dim"}}}]}
    with pytest.raises(RuntimeError, match="bulk index rejected"):
        repo.index([SearchDoc(id="d", world_id="w", label="NPC", text="t")])
