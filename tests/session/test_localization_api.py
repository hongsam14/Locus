"""X1 localization + region_changes over the session API (read-path enrichment,
lazy generate, advance-turn shaping)."""

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
from locus.translation import TranslationService, Translator


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


class _GraphRepo:
    def find_nodes(self, world_id, label, filters=None):
        if label == "Region" and world_id == "w":
            return [Node(id="r1", label="Region", world_id=world_id, properties={"id": "r1"})]
        return []


class _LLM:
    """structured() drives rumor generation; complete() drives translation ('KO:'+text)."""

    def structured(self, prompt, schema, *, system=None):
        return RumorDraft(statement="distorted")

    def complete(self, prompt, *, system=None):
        return "KO:" + prompt.split("Text:\n", 1)[-1]


class _Loader:
    def __init__(self) -> None:
        self.region = Region(world_id="w", name="R1", level=RegionLevel.TOWN, provenance=_prov())
        self.region.id = "r1"
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
    translation = TranslationService(repo, Translator(_LLM()))
    return TestClient(
        create_app(
            session_service=SessionService(repo, _GraphRepo()),
            game_master=GameMasterService(repo, RumorGenerator(_LLM()), loader),
            session_query=SessionQueryEngine(repo, loader, translation=translation),
            translation=translation,
        )
    )


def _start(client: TestClient) -> str:
    return client.post("/api/session/worlds/w/sessions").json()["id"]


def test_generate_null_then_cached_read_localizes() -> None:
    client = _client()
    sid = _start(client)
    gen = client.post(f"/api/session/sessions/{sid}/regions/r1/rumors").json()
    assert gen and all(r["statement_ko"] is None for r in gen)  # Q2=A: generate is lazy

    # Reads are cache-only (review #3): first read is a miss (null) but warms the
    # cache inline (test scheduler); the next read serves the translation.
    client.get(f"/api/session/sessions/{sid}/regions/r1/rumors")
    listed = client.get(f"/api/session/sessions/{sid}/regions/r1/rumors").json()
    assert listed and all(r["statement_ko"] == "KO:distorted" for r in listed)


def test_session_knowledge_is_localized_after_warm() -> None:
    client = _client()
    sid = _start(client)
    client.post(f"/api/session/sessions/{sid}/regions/r1/rumors")  # seed a rumor
    client.get(f"/api/session/sessions/{sid}/regions/r1/knowledge")  # warm
    res = client.get(f"/api/session/sessions/{sid}/regions/r1/knowledge").json()
    items = res["items"]
    canon = [it for it in items if not it["is_rumor"]]
    rumor = [it for it in items if it["is_rumor"]]
    assert canon and canon[0]["statement_ko"] == "KO:fact"
    assert rumor and rumor[0]["statement_ko"] == "KO:distorted"


def test_advance_turn_includes_region_changes() -> None:
    client = _client()
    sid = _start(client)
    res = client.post(f"/api/session/sessions/{sid}/advance-turn").json()
    assert "region_changes" in res and isinstance(res["region_changes"], list)


def test_translation_disabled_shows_original() -> None:
    # No translation service wired -> ko stays null (graceful, originals shown).
    repo = InMemorySessionRepository()
    loader = _Loader()
    client = TestClient(
        create_app(
            session_service=SessionService(repo, _GraphRepo()),
            game_master=GameMasterService(repo, RumorGenerator(_LLM()), loader),
            session_query=SessionQueryEngine(repo, loader),
        )
    )
    sid = _start(client)
    client.post(f"/api/session/sessions/{sid}/regions/r1/rumors")
    listed = client.get(f"/api/session/sessions/{sid}/regions/r1/rumors").json()
    assert listed and all(r["statement_ko"] is None for r in listed)
