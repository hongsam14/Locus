"""U8 serving API tests — FastAPI TestClient with a mocked QueryEngine."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from locus.models import KnowledgeView, QueryResult, RegionDiff


class _FakeEngine:
    def knowledge_for_region(self, world_id, region_id, *, include_rumors=True):
        if region_id == "missing":
            raise LookupError("region not found: missing")
        return QueryResult(
            world_id=world_id,
            region_id=region_id,
            items=[
                KnowledgeView(
                    knowledge_id="k1", statement="hi", scope_type="direct", confidence=0.9
                )
            ],
            shared_ids=["g1"],
            unique_ids=["k1"],
        )

    def diff_regions(self, world_id, region_a, region_b):
        return RegionDiff(
            world_id=world_id,
            region_a=region_a,
            region_b=region_b,
            shared_ids=["s1"],
            only_a_ids=["a1"],
            only_b_ids=["b1"],
        )


def _client() -> TestClient:
    return TestClient(create_app(query_engine=_FakeEngine()))


def test_health() -> None:
    assert _client().get("/health").json() == {"status": "ok"}


def test_region_knowledge_ok() -> None:
    r = _client().get("/api/query/regions/r1/knowledge", params={"world_id": "w"})
    assert r.status_code == 200
    body = r.json()
    assert body["region_id"] == "r1"
    assert body["unique_ids"] == ["k1"]
    assert body["items"][0]["knowledge_id"] == "k1"


def test_region_knowledge_missing_404() -> None:
    r = _client().get("/api/query/regions/missing/knowledge", params={"world_id": "w"})
    assert r.status_code == 404


def test_diff_ok() -> None:
    r = _client().get("/api/query/diff", params={"world_id": "w", "region_a": "a", "region_b": "b"})
    assert r.status_code == 200
    assert r.json()["shared_ids"] == ["s1"]


def test_missing_required_param_422() -> None:
    # world_id is required
    r = _client().get("/api/query/regions/r1/knowledge")
    assert r.status_code == 422
