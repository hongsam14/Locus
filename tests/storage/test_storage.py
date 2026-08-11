"""U1 storage tests — Cypher/query construction (mocked driver/client)."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from locus.storage import Neo4jGraphRepository, Node, build_search_body, index_mapping
from locus.storage.neo4j_repo import _safe_ident


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
    assert "n:World" not in queries


def test_traverse_respects_min_weight_param() -> None:
    rows = [{"node_ids": ["a", "b"], "total_weight": 0.5}]
    repo, recorder = _repo_with_fake_driver(rows)
    from locus.storage import TraversalSpec

    paths = repo.traverse("w1", "a", TraversalSpec(min_weight=0.3, max_depth=2))
    assert paths[0].node_ids == ["a", "b"]
    _, params = recorder[0]
    assert params["min_weight"] == 0.3


# --------------------------------------------------------------------------- #
# OpenSearch query construction (pure functions)
# --------------------------------------------------------------------------- #
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
