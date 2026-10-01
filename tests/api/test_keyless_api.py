"""TP-U8-8 (BR-U8-23·24, US-1.4, NFR-4): a server without an API key.

The app is assembled the production way with no LLM provider: the LLM routes of
business-logic-model §4.1 answer 503 (never 500), and the routes a visitor uses
without a key — the demo, a session, a move, a seed, augmentation, a prior — work.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from locus.knowledge.cache import WorldCache
from locus.knowledge.loader import WorldLoader
from locus.knowledge.wiring import KnowledgeContainer
from locus.play import InMemoryPlayRepository
from locus.play.turn.executor import SyncTurnExecutor
from locus.play.wiring import assemble_play
from locus.shared.config import Settings
from locus.shared.wiring import SharedContainer
from locus.world.wiring import assemble_world
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository

W = "emberleaf"  # the packaged demo, loaded into its own id (test input, BR-U8-1 allows it)


def _keyless():
    graph, search = InMemoryGraphRepository(), InMemorySearchRepository()
    shared = SharedContainer(settings=Settings(), graph=graph, search=search, llm=None)
    cache = WorldCache(WorldLoader(graph))
    knowledge = KnowledgeContainer(
        loader=WorldLoader(graph), cache=cache, query=None, params=None  # type: ignore[arg-type]
    )
    world = assemble_world(shared, knowledge)
    play = assemble_play(
        shared, knowledge, repo=InMemoryPlayRepository(), executor=SyncTurnExecutor()
    )
    client = TestClient(
        create_app(shared=shared, world=world, play=play), raise_server_exceptions=False
    )
    return client, play


def test_tp_u8_8_without_a_key_llm_routes_are_503_and_the_rest_works() -> None:
    client, play = _keyless()
    assert client.get("/api/capabilities").json() == {
        "llm": False,
        "vlm": False,
        "embedding": False,
    }
    assert client.get("/health").json()["status"] == "ok"

    # the visitor's path: demo -> session at the start region -> a move -> a seed
    demos = client.get("/api/world/demos").json()
    start = demos[0]["start_region_id"]
    assert client.post(f"/api/world/worlds/{W}/demo/{demos[0]['name']}").status_code == 200
    out = client.post(
        f"/api/play/worlds/{W}/sessions", json={"name": "Traveler", "start_region_id": start}
    )
    assert out.status_code == 201
    sid = out.json()["session"]["id"]
    act = client.post(
        f"/api/play/sessions/{sid}/act", json={"type": "move", "to_region_id": "region-ambermeadow"}
    )
    assert act.status_code == 202
    assert (
        client.post(f"/api/gm/sessions/{sid}/seeds/seed-mushroom-blight/start").status_code == 201
    )
    assert client.post(f"/api/world/worlds/{W}/augmentation/runs").status_code == 200
    prior = {
        "id": "prior-new",
        "world_id": W,
        "prior_type": "fact",
        "condition": "a harbor",
        "effect": "news arrives by ship",
        "provenance": {"source": "input"},
    }
    assert client.post(f"/api/world/worlds/{W}/priors", json=prior).status_code == 200

    # the LLM routes (BLM §4.1): 503, never 500
    llm_routes = [
        ("post", f"/api/world/worlds/{W}/build", {"json": {"memos": ["a note"]}}),
        ("post", f"/api/world/worlds/{W}/build/upload", {"files": {"memos": ("m.txt", b"note")}}),
        ("post", f"/api/world/worlds/{W}/demo/{demos[0]['name']}/build", {}),
        ("post", f"/api/world/worlds/{W}/regions/region-saltwake/npc-drafts", {}),
        ("post", f"/api/gm/sessions/{sid}/regions/region-saltwake/rumors", {}),
        ("post", f"/api/gm/sessions/{sid}/regions/region-saltwake/rumors/regen", {}),
        ("post", f"/api/gm/sessions/{sid}/events/suggest", {}),
        ("post", f"/api/play/sessions/{sid}/npcs/npc-brisa/say", {"json": {"text": "hello"}}),
    ]
    got = {path: getattr(client, verb)(path, **kw).status_code for verb, path, kw in llm_routes}
    assert all(code == 503 for code in got.values()), got
