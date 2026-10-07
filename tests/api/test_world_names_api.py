"""V3: the world name map and the Korean list fields (FD BLM § 8·9, BR-V3-03·21~23,
TP-V3-7 part, code plan R-03/R-08c). The app is assembled the production way with no
LLM, over in-memory graph, search and translation stores."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from locus.knowledge.wiring import assemble_knowledge
from locus.localization import (
    InMemoryTranslationRepository,
    LocalizationContainer,
    TranslationService,
    Translator,
    assemble_localization,
)
from locus.play import InMemoryPlayRepository
from locus.play.turn.executor import SyncTurnExecutor
from locus.play.wiring import assemble_play
from locus.shared.config import Settings
from locus.shared.wiring import SharedContainer
from locus.world.wiring import assemble_world
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository


def _app(*, loc: LocalizationContainer | None = None, keyless_loc: bool = True):
    graph, search = InMemoryGraphRepository(), InMemorySearchRepository()
    shared = SharedContainer(settings=Settings(), graph=graph, search=search, llm=None)
    knowledge = assemble_knowledge(shared)
    world = assemble_world(shared, knowledge)
    play = assemble_play(
        shared, knowledge, repo=InMemoryPlayRepository(), executor=SyncTurnExecutor()
    )
    if loc is None and keyless_loc:  # the keyless production path: a service with no translator
        loc = assemble_localization(shared, store=InMemoryTranslationRepository())
    app = create_app(shared=shared, world=world, play=play, localization=loc)
    return TestClient(app, raise_server_exceptions=False), world, loc


def _load_demo(client: TestClient) -> str:
    demo = client.get("/api/world/demos").json()[0]
    assert client.post(f"/api/world/worlds/{demo['name']}/demo/{demo['name']}").status_code == 200
    return demo["name"]


def _seed_directly(world, loc, name: str) -> None:
    """Rows straight into the cache (the load route seeds from Step 8's second commit)."""
    demo = world.demo
    entries = demo.translations(name, "ko", target_world_id=name, remapped=False)
    texts = demo.texts(name, target_world_id=name, remapped=False)
    assert (
        loc.translations.seed(entries, lang="ko", current_text=texts, world_id=name).seeded == 123
    )


def test_the_name_map_serves_the_cached_korean_by_id() -> None:
    client, world, loc = _app()
    name = _load_demo(client)
    before = client.get(f"/api/world/worlds/{name}/names").json()
    assert before["regions"] == {} and before["lang"] == "ko"  # nothing cached, no warm
    _seed_directly(world, loc, name)
    names = client.get(f"/api/world/worlds/{name}/names").json()
    assert names["world_id"] == name and names["world"]["name"] == "엠버리프 섬"
    assert (
        len(names["regions"]) == 12
        and names["regions"]["region-saltwake"]["name"] == "솔트웨이크 항구"
    )
    assert set(names["regions"]["region-saltwake"]) == {"name", "description"}
    assert len(names["npcs"]) == 15 and names["npcs"]["npc-brisa"] == {
        "name": "브리사 대장",
        "role": "궁수대장",
        "description": "무너진 절벽 길을 지키는 궁수들을 이끈다.",
    }
    assert len(names["event_seeds"]) == 3


def test_the_source_language_a_bad_language_and_a_missing_world() -> None:
    client, world, loc = _app()
    name = _load_demo(client)
    _seed_directly(world, loc, name)
    en = client.get(f"/api/world/worlds/{name}/names?lang=en").json()
    assert en["lang"] == "en" and en["regions"] == en["npcs"] == en["world"] == {}
    bad = client.get(f"/api/world/worlds/{name}/names?lang=xx")
    assert bad.status_code == 400 and bad.json()["code"] == "unsupported_lang"
    missing = client.get("/api/world/worlds/nowhere/names")
    assert missing.status_code == 404 and missing.json()["code"] == "not_found"


def test_without_localization_the_map_is_empty_and_without_a_cache_it_is_503() -> None:
    client, _world, _loc = _app(keyless_loc=False)
    name = _load_demo(client)
    names = client.get(f"/api/world/worlds/{name}/names").json()
    assert names["regions"] == {} and names["world"] == {}
    client, world, _loc = _app()
    world.cache = None  # code plan memo R-03
    r = client.get(f"/api/world/worlds/{name}/names")
    assert r.status_code == 503 and r.json()["code"] == "service_unavailable"


def test_the_world_list_and_demo_cards_carry_korean() -> None:
    client, world, loc = _app()
    name = _load_demo(client)
    row = next(w for w in client.get("/api/world/worlds").json() if w["id"] == name)
    assert row["name_ko"] is None  # not cached yet
    _seed_directly(world, loc, name)
    row = next(w for w in client.get("/api/world/worlds").json() if w["id"] == name)
    assert row["name_ko"] == "엠버리프 섬" and row["description_ko"].endswith("다.")
    assert (
        next(w for w in client.get("/api/world/worlds?lang=en").json() if w["id"] == name)[
            "name_ko"
        ]
        is None
    )
    card = client.get("/api/world/demos").json()[0]
    assert card["title_ko"] == "엠버리프 섬" and card["credits_ko"] and card["description_ko"]
    assert client.get("/api/world/demos?lang=en").json()[0]["title_ko"] is None


def test_demo_cards_are_korean_with_no_database_at_all() -> None:  # BR-V3-23
    client, _w, _l = _app(keyless_loc=False)
    assert client.get("/api/world/demos").json()[0]["title_ko"] == "엠버리프 섬"


class _LLM:
    def complete(self, prompt, *, system=None):
        return "KO"

    def structured(self, prompt, schema, *, system=None):  # pragma: no cover
        raise NotImplementedError


def test_with_an_llm_the_map_hands_its_misses_to_the_warm() -> None:  # code plan R-08 (c)
    scheduled: list = []
    service = TranslationService(
        InMemoryTranslationRepository(), Translator(_LLM()), warm_scheduler=scheduled.append
    )
    client, _world, _loc = _app(loc=LocalizationContainer(translations=service))
    name = _load_demo(client)
    assert client.get(f"/api/world/worlds/{name}/names").json()["regions"] == {}
    assert scheduled  # the region, NPC, seed and world misses went to the warm
