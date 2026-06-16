"""S1+S2 session API tests — FastAPI TestClient with in-memory services."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from locus.models import (
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
from locus.session import (
    GameMasterService,
    InMemorySessionRepository,
    SessionQueryEngine,
    SessionService,
)
from locus.session.rumor_generator import RumorDraft, RumorGenerator
from locus.storage.base import Node


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


class _GraphRepo:
    def find_nodes(self, world_id, label, filters=None):
        if label == "Region" and world_id == "w":
            return [Node(id="r1", label="Region", world_id=world_id, properties={"id": "r1"})]
        return []


class _FakeLLM:
    def structured(self, prompt, schema, *, system=None):
        return RumorDraft(statement="distorted")

    def complete(self, prompt, *, system=None):  # pragma: no cover
        return ""


class _Loader:
    def __init__(self) -> None:
        self.region = Region(world_id="w", name="R1", level=RegionLevel.TOWN, provenance=_prov())
        self.region.id = "r1"  # match the graph repo region id
        k = Knowledge(world_id="w", statement="fact", title="t", provenance=_prov())
        scope = ScopeLink(
            world_id="w", knowledge_id=k.id, region_id="r1", scope_type=ScopeType.DIRECT
        )
        self._kg = KnowledgeGraph(world_id="w", knowledge=[k], scopes=[scope])
        self._topo = RegionTopology(world_id="w", regions=[self.region])

    def load(self, world_id):
        return self._kg, self._topo


def _client() -> TestClient:
    repo = InMemorySessionRepository()
    loader = _Loader()
    return TestClient(
        create_app(
            session_service=SessionService(repo, _GraphRepo()),
            game_master=GameMasterService(repo, RumorGenerator(_FakeLLM()), loader),
            session_query=SessionQueryEngine(repo, loader),
        )
    )


def test_start_list_get_close_flow() -> None:
    client = _client()
    r = client.post("/api/session/worlds/w/sessions")
    assert r.status_code == 200
    session = r.json()
    assert session["status"] == "open" and session["turn"] == 0
    sid = session["id"]

    hist = client.get("/api/session/worlds/w/sessions")
    assert hist.status_code == 200 and len(hist.json()) == 1

    got = client.get(f"/api/session/sessions/{sid}")
    assert got.status_code == 200 and got.json()["id"] == sid

    closed = client.post(f"/api/session/sessions/{sid}/close")
    assert closed.status_code == 200 and closed.json()["status"] == "closed"

    timeline = client.get(f"/api/session/sessions/{sid}/timeline")
    assert timeline.status_code == 200 and timeline.json() == []


def test_start_unknown_world_404() -> None:
    client = _client()
    r = client.post("/api/session/worlds/missing/sessions")
    assert r.status_code == 404


def test_get_missing_session_404() -> None:
    client = _client()
    assert client.get("/api/session/sessions/nope").status_code == 404
    assert client.post("/api/session/sessions/nope/close").status_code == 404
    assert client.get("/api/session/sessions/nope/timeline").status_code == 404


# --- S2 routes -------------------------------------------------------------- #
def _new_session(client: TestClient) -> str:
    return client.post("/api/session/worlds/w/sessions").json()["id"]


def test_generate_support_advance_and_knowledge_flow() -> None:
    client = _client()
    sid = _new_session(client)

    gen = client.post(f"/api/session/sessions/{sid}/regions/r1/rumors")
    assert gen.status_code == 200
    rumors = gen.json()
    assert len(rumors) == 3
    rid = rumors[0]["id"]

    sup = client.put(f"/api/session/sessions/{sid}/rumors/{rid}/support", json={"support": 0.9})
    assert sup.status_code == 200 and sup.json()["support"] == 0.9

    turn = client.post(f"/api/session/sessions/{sid}/advance-turn")
    assert turn.status_code == 200
    body = turn.json()
    assert body["turn"] == 1 and rid in body["promoted_ids"]

    listed = client.get(f"/api/session/sessions/{sid}/regions/r1/rumors")
    assert listed.status_code == 200 and len(listed.json()) == 3  # read-only list

    know = client.get(f"/api/session/sessions/{sid}/regions/r1/knowledge")
    assert know.status_code == 200
    assert rid in know.json()["unique_ids"]  # promoted rumor is direct-like


def test_set_distortion_and_regen() -> None:
    client = _client()
    sid = _new_session(client)
    dist = client.put(f"/api/session/sessions/{sid}/regions/r1/distortion", json={"degree": 0.8})
    assert dist.status_code == 200 and dist.json()["distortion_degree"] == 0.8
    regen = client.post(f"/api/session/sessions/{sid}/regions/r1/rumors/regen")
    assert regen.status_code == 200


def test_s2_validation_and_status_codes() -> None:
    client = _client()
    sid = _new_session(client)
    # 422 on out-of-range support is allowed via model? support is plain float -> clamp in service.
    # missing session -> 404
    assert client.post("/api/session/sessions/nope/regions/r1/rumors").status_code == 404
    assert client.get("/api/session/sessions/nope/regions/r1/rumors").status_code == 404
    assert client.post("/api/session/sessions/nope/advance-turn").status_code == 404
    # closed session -> 409
    client.post(f"/api/session/sessions/{sid}/close")
    assert client.post(f"/api/session/sessions/{sid}/regions/r1/rumors").status_code == 409
    assert client.post(f"/api/session/sessions/{sid}/advance-turn").status_code == 409
