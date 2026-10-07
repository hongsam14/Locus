"""knowledge router tests — FastAPI TestClient with a fake QueryEngine in a KnowledgeContainer."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from locus.knowledge.consensus import DEFAULT_PARAMS
from locus.knowledge.wiring import KnowledgeContainer
from locus.shared.models import KnowledgeView, QueryResult, RegionDiff


class _FakeEngine:
    def knowledge_for_region(self, world_id, region_id, *, include_hearsay=True):
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

    def region_briefs(self, world_id, *, top_k=3):
        from locus.shared.models import RegionBrief

        if world_id == "missing":
            raise LookupError("world not found: missing")
        return [
            RegionBrief(
                region_id="r1",
                name="Riverton",
                level="town",
                level_path=["Riverton"],
                top_knowledge=["Market"][:top_k],
            )
        ]

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
    container = KnowledgeContainer(
        loader=None, cache=None, query=_FakeEngine(), params=DEFAULT_PARAMS
    )
    return TestClient(create_app(knowledge=container))


def test_health_reports_boundaries() -> None:
    body = _client().get("/health").json()
    assert body["status"] == "ok"
    assert body["boundaries"]["knowledge"] is True and body["boundaries"]["play"] is False


def test_health_503_when_no_boundary_is_up() -> None:
    # nothing injected and assembly switched off -> every boundary None (review U1 #4)
    client = TestClient(create_app(assemble_missing=False))
    r = client.get("/health")
    assert r.status_code == 503 and r.json()["status"] == "unavailable"


def test_region_knowledge_ok() -> None:
    r = _client().get("/api/knowledge/worlds/w/regions/r1")
    assert r.status_code == 200
    body = r.json()
    assert body["region_id"] == "r1"
    assert body["unique_ids"] == ["k1"]
    assert body["items"][0]["knowledge_id"] == "k1"
    # display-only fields ride on the response DTO, not the domain model
    assert body["items"][0]["statement_ko"] is None


def test_region_knowledge_missing_404() -> None:
    r = _client().get("/api/knowledge/worlds/w/regions/missing")
    assert r.status_code == 404


def test_diff_ok() -> None:
    r = _client().get("/api/knowledge/worlds/w/diff", params={"region_a": "a", "region_b": "b"})
    assert r.status_code == 200
    assert r.json()["shared_ids"] == ["s1"]


def test_missing_required_param_422() -> None:
    # region_a / region_b are required
    r = _client().get("/api/knowledge/worlds/w/diff")
    assert r.status_code == 422


def test_boundary_unavailable_503() -> None:
    """US-7.2: a boundary that was not assembled answers 503 on its routes only."""
    client = TestClient(create_app(knowledge=_client().app.state.containers.knowledge))
    assert client.get("/api/knowledge/worlds/w/regions/r1").status_code == 200
    assert client.get("/api/play/worlds/w/sessions").status_code == 503
    assert client.get("/api/world/worlds/w/export").status_code == 503
    assert client.get("/api/gm/sessions/s/timeline").status_code == 503


def test_region_briefs_endpoint() -> None:  # U2 A5 / BR-U2-20
    r = _client().get("/api/knowledge/worlds/w/briefs?top_k=1")
    assert r.status_code == 200 and r.json()[0]["top_knowledge"] == ["Market"]
    assert _client().get("/api/knowledge/worlds/missing/briefs").status_code == 404
    assert _client().get("/api/knowledge/worlds/w/briefs?top_k=99").status_code == 422
