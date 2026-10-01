"""Shared assembly degrades per resource (review U1 #4) and SQL adapters never
dispose an injected engine (review U1 #14)."""

from __future__ import annotations

import pytest
from pydantic import SecretStr
from sqlalchemy import create_engine

from locus.localization.storage.postgres_repo import PostgresTranslationRepository
from locus.play.storage.postgres_repo import PostgresPlayRepository
from locus.shared import wiring
from locus.shared.config import Settings


class _DeadNeo4j:
    def __init__(self, **kw) -> None:
        self.disconnected = False

    def connect(self) -> None:
        raise ConnectionError("neo4j down")

    def disconnect(self) -> None:
        self.disconnected = True


class _LiveSearch:
    instances: list["_LiveSearch"] = []

    def __init__(self, **kw) -> None:
        self.disconnected = False
        _LiveSearch.instances.append(self)

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        self.disconnected = True


def _settings() -> Settings:
    return Settings.model_construct(
        neo4j_uri="bolt://x:1",
        neo4j_user="u",
        neo4j_password=SecretStr("p"),
        opensearch_url="http://x:1",
        opensearch_index="i",
        embedding_dimension=8,
        session_db_url=None,
    )


def test_non_strict_assembly_leaves_failed_resource_none(monkeypatch) -> None:
    monkeypatch.setattr(wiring, "Neo4jGraphRepository", _DeadNeo4j)
    monkeypatch.setattr(wiring, "OpenSearchRepository", _LiveSearch)
    c = wiring.assemble_shared(_settings(), llm=False, sql=False, strict=False)
    assert c.graph is None and c.search is not None  # search still assembled


def test_strict_assembly_raises_and_closes_what_it_opened(monkeypatch) -> None:
    _LiveSearch.instances.clear()
    monkeypatch.setattr(wiring, "OpenSearchRepository", _LiveSearch)
    monkeypatch.setattr(wiring, "Neo4jGraphRepository", _DeadNeo4j)
    # search is opened after graph in assemble order, so open search first via a
    # container whose graph step fails later: emulate by requesting both and
    # making the failure happen on the *second* resource.
    monkeypatch.setattr(wiring, "Neo4jGraphRepository", _LiveSearch)  # graph "connects"
    monkeypatch.setattr(wiring, "OpenSearchRepository", _DeadNeo4j)  # search fails
    with pytest.raises(ConnectionError):
        wiring.assemble_shared(_settings(), llm=False, sql=False, strict=True)
    assert _LiveSearch.instances and _LiveSearch.instances[-1].disconnected


@pytest.mark.parametrize("cls", [PostgresPlayRepository, PostgresTranslationRepository])
def test_injected_engine_survives_disconnect(cls) -> None:
    engine = create_engine("sqlite://", future=True)
    repo = cls(engine=engine)
    repo.disconnect()
    repo.ensure_schema()  # still bound to the shared engine, not disposed
    assert repo._engine is engine


def test_owned_engine_is_disposed_on_disconnect() -> None:
    repo = PostgresPlayRepository("sqlite://")
    repo.connect()
    repo.disconnect()
    assert repo._engine is None


def test_play_assembles_without_llm_and_gm_routes_answer_503() -> None:  # review #7
    from fastapi.testclient import TestClient

    from api.main import create_app
    from locus.knowledge.consensus import DEFAULT_PARAMS
    from locus.knowledge.query import QueryEngine
    from locus.knowledge.wiring import KnowledgeContainer
    from locus.play.storage.memory_repo import InMemoryPlayRepository
    from locus.play.wiring import assemble_play
    from locus.shared.wiring import SharedContainer
    from tests.api.play_fixtures import GraphRepo, Loader

    loader = Loader()
    shared = SharedContainer(settings=Settings.model_construct(), graph=GraphRepo(), llm=None)
    knowledge = KnowledgeContainer(
        loader=None, cache=loader, query=QueryEngine(loader), params=DEFAULT_PARAMS
    )
    play = assemble_play(shared, knowledge, repo=InMemoryPlayRepository())
    # U4-2 #13: every service is assembled; only the LLM-needing *methods* refuse.
    assert play.sessions is not None and play.rumors is not None and play.events is not None
    assert not play.rumors.llm_available and not play.events.llm_available
    assert play.turns is not None and not play.turns.llm_available  # engine runs LLM-free
    client = TestClient(create_app(play=play))
    sid = client.post("/api/play/worlds/w/sessions").json()["id"]  # session lifecycle works
    assert client.get(f"/api/play/sessions/{sid}").status_code == 200
    r = client.post(f"/api/gm/sessions/{sid}/regions/r1/rumors")
    assert r.status_code == 503 and "OPENAI_API_KEY" in r.json()["detail"]
    # ... while the deterministic event lifecycle and rumor reads keep working (U4-2 #13)
    assert client.get(f"/api/gm/sessions/{sid}/events").status_code == 200
    assert client.get(f"/api/gm/sessions/{sid}/regions/r1/rumors").status_code == 200
    created = client.post(
        f"/api/gm/sessions/{sid}/events",
        json={"region_id": "r1", "category": "war", "magnitude": 0.5},
    )
    assert created.status_code == 200
    eid = created.json()["id"]
    assert client.post(f"/api/gm/sessions/{sid}/events/{eid}/resolve").status_code == 200
    assert client.post(f"/api/gm/sessions/{sid}/events/suggest").status_code == 503
    assert client.post(f"/api/gm/sessions/{sid}/advance").status_code == 200  # U4 contract (5)
    assert client.get(f"/api/gm/sessions/{sid}/distortions").status_code == 200
