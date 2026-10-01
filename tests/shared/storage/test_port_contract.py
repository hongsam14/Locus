"""Graph/search port contract (U3, domain-entities §1, TP-U3-3, NFR R-06).

Behaviour is checked against the in-memory fakes every offline test uses; the Neo4j
and OpenSearch adapters are checked for the shape of what they send (the live run is
operator-only, code-summary §12.2).
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest
from hypothesis import given
from hypothesis import strategies as st

from locus.shared.models import SearchDoc
from locus.shared.storage import EdgeKey, Neo4jGraphRepository, OpenSearchRepository
from locus.shared.storage.base import ConstraintViolation, Edge, Node
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository

_KEYS = st.sampled_from(["name", "description", "parent_id", "position", "level", "tags"])
_VALUES = st.one_of(st.text(max_size=8), st.integers(-5, 5), st.none())
_PROPS = st.dictionaries(_KEYS, _VALUES, max_size=6)


# --------------------------------------------------------------------------- #
# replace_nodes (TP-U3-3)
# --------------------------------------------------------------------------- #
@given(first=_PROPS, second=_PROPS)
def test_tp_u3_3_replace_keeps_exactly_the_written_properties(first: dict, second: dict) -> None:
    """TP-U3-3: after a replace, the node holds exactly the written properties —
    a property left out is gone; id and world_id stay."""
    g = InMemoryGraphRepository()
    g.upsert_nodes([Node(id="r1", label="Region", world_id="w", properties=first)])
    g.replace_nodes([Node(id="r1", label="Region", world_id="w", properties=second)])
    got = g.get_node("w", "r1")
    assert got is not None
    assert (got.id, got.world_id, got.label) == ("r1", "w", "Region")
    assert got.properties == second


def test_replace_creates_a_missing_node() -> None:
    g = InMemoryGraphRepository()
    g.replace_nodes([Node(id="k1", label="Knowledge", world_id="w", properties={"a": 1})])
    assert g.get_node("w", "k1").properties == {"a": 1}  # type: ignore[union-attr]


def test_replace_rejects_an_id_of_another_world() -> None:
    g = InMemoryGraphRepository()
    g.upsert_nodes([Node(id="x", label="Region", world_id="other", properties={})])
    with pytest.raises(ConstraintViolation):
        g.replace_nodes([Node(id="x", label="Region", world_id="w", properties={})])


def test_merge_upsert_is_unchanged() -> None:
    """Build and import keep the merge write (U3 changes only editor writes)."""
    g = InMemoryGraphRepository()
    g.upsert_nodes([Node(id="r1", label="Region", world_id="w", properties={"a": 1})])
    g.upsert_nodes([Node(id="r1", label="Region", world_id="w", properties={"b": 2})])
    assert g.get_node("w", "r1").properties == {"a": 1, "b": 2}  # type: ignore[union-attr]


# --------------------------------------------------------------------------- #
# delete_edges
# --------------------------------------------------------------------------- #
def _road_and_river() -> InMemoryGraphRepository:
    g = InMemoryGraphRepository()
    for kind, weight in (("route", 0.6), ("river", 0.4)):
        g.upsert_edges(
            [
                Edge(
                    type="CONNECTED_TO",
                    source_id="a",
                    target_id="b",
                    world_id="w",
                    properties={"kind": kind, "weight": weight},
                )
            ]
        )
    g.upsert_edges([Edge(type="CONTAINS", source_id="p", target_id="a", world_id="w")])
    return g


def test_delete_edges_by_identity_leaves_the_parallel_edge() -> None:
    g = _road_and_river()
    n = g.delete_edges(
        "w",
        [EdgeKey(type="CONNECTED_TO", source_id="a", target_id="b", identity={"kind": "route"})],
    )
    assert n == 1
    left = g.get_edges("w", ["CONNECTED_TO"])
    assert [e.properties["kind"] for e in left] == ["river"]


def test_delete_edges_without_identity_matches_every_parallel_edge() -> None:
    g = _road_and_river()
    assert g.delete_edges("w", [EdgeKey(type="CONNECTED_TO", source_id="a", target_id="b")]) == 2
    assert g.get_edges("w", ["CONTAINS"])  # other types untouched


def test_delete_edges_skips_missing_and_other_worlds() -> None:
    g = _road_and_river()
    missing = [
        EdgeKey(type="CONNECTED_TO", source_id="b", target_id="a"),  # wrong direction
        EdgeKey(type="SCOPED_TO", source_id="k", target_id="a"),
    ]
    assert g.delete_edges("w", missing) == 0
    assert g.delete_edges("other", [EdgeKey(type="CONTAINS", source_id="p", target_id="a")]) == 0
    assert len(g.get_edges("w")) == 3


# --------------------------------------------------------------------------- #
# SearchRepository.delete
# --------------------------------------------------------------------------- #
def _doc(world: str, doc_id: str) -> SearchDoc:
    return SearchDoc(id=doc_id, world_id=world, label="Knowledge", text="t")


def test_search_delete_counts_and_skips_missing() -> None:
    s = InMemorySearchRepository()
    s.index([_doc("w", "k1"), _doc("w", "k2"), _doc("other", "k3")])
    assert s.delete("w", ["k1", "nope", "k3"]) == 1  # k3 belongs to another world
    assert set(s.docs) == {("w", "k2"), ("other", "k3")}
    assert s.delete("w", []) == 0


# --------------------------------------------------------------------------- #
# Neo4j adapter shape (fake driver, test_storage.py pattern)
# --------------------------------------------------------------------------- #
class _Session:
    def __init__(self, recorder: list, rows: list[dict], fail: Exception | None) -> None:
        self._recorder, self._rows, self._fail = recorder, rows, fail

    def run(self, query: str, **params):
        self._recorder.append((query, params))
        if self._fail is not None:
            raise self._fail
        records = []
        for r in self._rows:
            rec = MagicMock()
            rec.data.return_value = r
            records.append(rec)
        return records


def _neo4j(rows: list[dict] | None = None, fail: Exception | None = None):
    recorder: list[tuple[str, dict]] = []
    repo = Neo4jGraphRepository(uri="bolt://x", user="u", password="p")
    driver = MagicMock()

    @contextmanager
    def _session():
        yield _Session(recorder, rows or [], fail)

    driver.session.side_effect = _session
    repo._driver = driver
    return repo, recorder


def test_neo4j_replace_nodes_is_one_unwind_per_label_and_keeps_identity() -> None:
    repo, rec = _neo4j()
    repo.replace_nodes(
        [
            Node(id="r1", label="Region", world_id="w", properties={"name": "A"}),
            Node(id="r2", label="Region", world_id="w", properties={"name": "B"}),
            Node(id="k1", label="Knowledge", world_id="w", properties={"statement": "s"}),
        ]
    )
    assert len(rec) == 2  # one query per label (NFR R-06)
    query, params = rec[0]
    assert query.startswith("UNWIND $rows AS row")
    assert "MERGE (n:Region {id: row.id, world_id: row.world_id})" in query
    assert "SET n = row.props" in query and "+=" not in query
    assert params["rows"][0]["props"] == {"name": "A", "id": "r1", "world_id": "w"}


def test_neo4j_replace_nodes_translates_the_constraint_error() -> None:
    class ConstraintError(Exception):  # matched by name, like the lazy driver import
        pass

    repo, _ = _neo4j(fail=ConstraintError("dup"))
    with pytest.raises(ConstraintViolation):
        repo.replace_nodes([Node(id="r1", label="Region", world_id="w", properties={})])


def test_neo4j_delete_edges_groups_by_type_and_identity() -> None:
    repo, rec = _neo4j(rows=[{"n": 2}])
    n = repo.delete_edges(
        "w",
        [
            EdgeKey(type="CONNECTED_TO", source_id="a", target_id="b", identity={"kind": "route"}),
            EdgeKey(type="CONNECTED_TO", source_id="b", target_id="a", identity={"kind": "route"}),
            EdgeKey(type="SCOPED_TO", source_id="k", target_id="a"),
        ],
    )
    assert len(rec) == 2  # (CONNECTED_TO, kind) and (SCOPED_TO, -)
    conn = next(q for q, _ in rec if "CONNECTED_TO" in q)
    scope = next(q for q, _ in rec if "SCOPED_TO" in q)
    assert "[r:CONNECTED_TO {kind: row.k.kind}]" in conn
    assert "[r:SCOPED_TO]" in scope
    assert all("DELETE r RETURN count(r) AS n" in q for q, _ in rec)
    assert n == 4  # the fake driver answers n=2 to each query


def test_neo4j_delete_edges_rejects_an_unsafe_identity_key() -> None:
    repo, _ = _neo4j()
    with pytest.raises(ValueError):
        repo.delete_edges(
            "w",
            [EdgeKey(type="X", source_id="a", target_id="b", identity={"k}) DETACH DELETE": 1})],
        )


# --------------------------------------------------------------------------- #
# OpenSearch adapter shape (fake client)
# --------------------------------------------------------------------------- #
def test_opensearch_delete_filters_by_world_and_ids() -> None:
    repo = OpenSearchRepository(url="http://x", index="i", vector_dimension=4)
    client = MagicMock()
    client.delete_by_query.return_value = {"deleted": 2}
    repo._client = client
    assert repo.delete("w", ["k1", "k2"]) == 2
    body = client.delete_by_query.call_args.kwargs["body"]
    assert body == {
        "query": {
            "bool": {"filter": [{"term": {"world_id": "w"}}, {"ids": {"values": ["k1", "k2"]}}]}
        }
    }
    assert repo.delete("w", []) == 0
    assert client.delete_by_query.call_count == 1


# --------------------------------------------------------------------------- #
# U8: replace_edges and edges_touching (U3 code review #13, C10)
# --------------------------------------------------------------------------- #
def _conn(**props) -> Edge:
    return Edge(
        type="CONNECTED_TO",
        source_id="a",
        target_id="b",
        world_id="w",
        properties={"kind": "route", **props},
    )


def test_replace_edges_keeps_exactly_the_written_properties() -> None:
    """A cleared prior ref is gone after a replace; the identity (kind) still matches."""
    g = InMemoryGraphRepository()
    g.upsert_edges([_conn(weight=0.5, wiki_prior_ref="p1")])
    g.replace_edges([_conn(weight=0.5)])
    (edge,) = g.get_edges("w")
    assert edge.properties == {"kind": "route", "weight": 0.5}


def test_neo4j_replace_edges_merges_by_identity_and_sets_the_whole_map() -> None:
    repo, rec = _neo4j()
    repo.replace_edges([_conn(weight=0.5)])
    ((query, params),) = rec
    assert "MERGE (a)-[r:CONNECTED_TO {kind: $key}]->(b)" in query
    assert "SET r = $props" in query and params["key"] == "route"


def test_edges_touching_returns_only_edges_with_an_end_in_the_ids() -> None:
    g = InMemoryGraphRepository()
    g.upsert_edges(
        [
            _conn(),
            Edge(type="LIVES_IN", source_id="n1", target_id="b", world_id="w"),
            Edge(type="LIVES_IN", source_id="n2", target_id="c", world_id="w"),
        ]
    )
    got = {(e.type, e.source_id) for e in g.edges_touching("w", ["b"])}
    assert got == {("CONNECTED_TO", "a"), ("LIVES_IN", "n1")}
    assert [e.source_id for e in g.edges_touching("w", ["b"], ["LIVES_IN"])] == ["n1"]
    assert g.edges_touching("w", []) == []
    repo, rec = _neo4j()
    repo.edges_touching("w", ["b"], ["LIVES_IN"])
    ((query, params),) = rec
    assert "a.id IN $ids OR b.id IN $ids" in query and params["types"] == ["LIVES_IN"]
