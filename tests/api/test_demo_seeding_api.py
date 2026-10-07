"""V3: a demo load seeds its translations; replaces, region and NPC deletes purge them;
a seed's translation moves to its event (FD BLM § 3·7·10, BR-V3-13~17·25,
TP-V3-7·8·10, code plan R-04/R-07/R-08b). Keyless production assembly, in-memory stores."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from locus.knowledge.wiring import assemble_knowledge
from locus.localization import InMemoryTranslationRepository, Translation, assemble_localization
from locus.play import InMemoryPlayRepository
from locus.play.turn.executor import SyncTurnExecutor
from locus.play.wiring import assemble_play
from locus.shared.config import Settings
from locus.shared.wiring import SharedContainer
from locus.world.wiring import assemble_world
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository


def _app(store: InMemoryTranslationRepository | None = None):
    store = store if store is not None else InMemoryTranslationRepository()
    graph, search = InMemoryGraphRepository(), InMemorySearchRepository()
    shared = SharedContainer(settings=Settings(), graph=graph, search=search, llm=None)
    knowledge = assemble_knowledge(shared)
    world = assemble_world(shared, knowledge)
    play = assemble_play(
        shared, knowledge, repo=InMemoryPlayRepository(), executor=SyncTurnExecutor()
    )
    loc = assemble_localization(shared, store=store)  # keyless: no translator
    client = TestClient(
        create_app(shared=shared, world=world, play=play, localization=loc),
        raise_server_exceptions=False,
    )
    return client, store


def _demo(client: TestClient) -> dict:
    return client.get("/api/world/demos").json()[0]


def _load(client: TestClient, world_id: str | None = None, **params):
    demo = _demo(client)
    return client.post(
        f"/api/world/worlds/{world_id or demo['name']}/demo/{demo['name']}", params=params
    )


def _rows(store: InMemoryTranslationRepository) -> list[Translation]:
    return list(store._translations.values())  # noqa: SLF001


# --- seeding (TP-V3-7) ------------------------------------------------------------- #
def test_a_keyless_load_seeds_every_text_and_the_player_reads_korean() -> None:
    client, store = _app()
    r = _load(client)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] and body["translations_seeded"] == 123 and body["translations_stale"] == 0
    assert len(_rows(store)) == 123 and {t.world_id for t in _rows(store)} == {
        _demo(client)["name"]
    }
    # the player's region screen: canonical facts carry their Korean
    w = _demo(client)["name"]
    out = client.post(
        f"/api/play/worlds/{w}/sessions",
        json={"name": "T", "start_region_id": _demo(client)["start_region_id"]},
    )
    view = client.get(f"/api/play/sessions/{out.json()['session']['id']}/region").json()
    assert view["facts"] and all(f["statement_ko"] for f in view["facts"])
    names = client.get(f"/api/world/worlds/{w}/names").json()
    assert names["regions"][view["region_id"]]["name"] == "솔트웨이크 항구"


def test_loading_again_seeds_the_same_rows() -> None:
    client, store = _app()
    _load(client)
    again = _load(client, confirm="true")
    assert again.status_code == 200 and again.json()["translations_seeded"] == 123
    assert len(_rows(store)) == 123  # purged, then seeded again: no duplicates


def test_a_demo_loaded_under_another_id_seeds_under_the_moved_ids() -> None:  # BR-V3-18·19
    client, store = _app()
    r = _load(client, world_id="w2")
    assert r.json()["remapped"] and r.json()["translations_seeded"] == 123
    names = client.get("/api/world/worlds/w2/names").json()
    assert len(names["regions"]) == 12 and names["world"]["name"] == "엠버리프 섬"
    assert "region-saltwake" not in names["regions"]  # the ids moved with the file
    assert {t.world_id for t in _rows(store)} == {"w2"}


class _SeedFails(InMemoryTranslationRepository):
    def upsert_many(self, translations):
        raise RuntimeError("database down")


class _PurgeFails(InMemoryTranslationRepository):
    def purge(self, **kw):
        raise RuntimeError("database down")


def test_a_failing_cache_never_breaks_the_load() -> None:  # code plan R-08 (b)
    client, _store = _app(_SeedFails())
    r = _load(client)
    assert r.status_code == 200 and r.json()["ok"] and r.json()["translations_seeded"] == 0
    client, _store = _app(_PurgeFails())
    _load(client)
    r = _load(client, confirm="true")  # a replace purges first
    assert r.status_code == 200 and r.json()["translations_seeded"] == 123


# --- purge (TP-V3-8) ------------------------------------------------------------------ #
def _row(
    kind: str, id_: str, *, world_id: str | None = None, session_id: str | None = None
) -> Translation:
    return Translation(
        source_kind=kind,
        source_id=id_,
        source_field="name",
        text="x",
        source_hash="h",
        world_id=world_id,
        session_id=session_id,
    )


def test_a_replace_keeps_the_rows_of_ids_still_held_and_drops_the_rest() -> None:
    # BR-V3-13 as corrected by code review 01 #1: rows of ids the new world lacks go
    client, store = _app()
    _load(client)
    w = _demo(client)["name"]
    store.upsert_many(
        [
            _row("region", "elsewhere", world_id="other"),
            _row("rumor", "ru1", session_id="s1"),
            _row("world", w),  # the world list's warm writes the world's name unmarked
            _row("region", "stale-region", world_id=w),  # an id the new world lacks
        ]
    )
    assert _load(client, confirm="true").status_code == 200
    ids = {t.source_id for t in _rows(store)}
    assert {"elsewhere", "ru1", w} <= ids and "stale-region" not in ids
    assert len([t for t in _rows(store) if t.world_id == w]) == 123


def test_re_importing_the_same_world_file_keeps_its_korean() -> None:  # review 01 #1
    client, store = _app()
    _load(client)
    w = _demo(client)["name"]
    file = client.get(f"/api/world/worlds/{w}/file").json()
    r = client.post(
        f"/api/world/worlds/{w}/file", params={"replace": "true", "confirm": "true"}, json=file
    )
    assert r.status_code == 200 and r.json()["replaced"]
    assert len([t for t in _rows(store) if t.world_id == w]) == 123
    names = client.get(f"/api/world/worlds/{w}/names").json()
    assert names["regions"]["region-saltwake"]["name"] == "솔트웨이크 항구"


def test_when_the_world_cannot_be_read_every_row_and_the_name_rows_go() -> None:  # BR-V3-13
    from api.schemas import purge_world_translations

    client, store = _app()
    _load(client)
    w = _demo(client)["name"]
    store.upsert_many([_row("world", w, world_id=None), _row("region", "x", world_id="other")])
    loc = client.app.state.containers.localization
    purge_world_translations(loc, w, None)  # e.g. a failed replace left no world
    left = _rows(store)
    assert not [
        t for t in left if t.world_id == w or (t.source_kind == "world" and t.source_id == w)
    ]
    assert [t.source_id for t in left] == ["x"]


def test_deleting_a_region_or_an_npc_drops_their_rows() -> None:  # BR-V3-16
    client, store = _app()
    _load(client)
    w = _demo(client)["name"]
    plan = client.get(f"/api/world/worlds/{w}/regions/region-ambermeadow/delete-plan").json()
    gone = {"region-ambermeadow", *(n["id"] for n in plan["npcs"]), *plan.get("seed_ids", [])}
    assert len(gone) > 2  # the region, its NPCs and its seed
    assert client.delete(f"/api/world/worlds/{w}/regions/region-ambermeadow").status_code == 200
    left = {t.source_id for t in _rows(store)}
    assert not (gone & left) and "region-saltwake" in left
    assert client.delete(f"/api/world/worlds/{w}/npcs/npc-pell").status_code == 204
    assert "npc-pell" not in {t.source_id for t in _rows(store)}
    assert "region-saltwake" in {t.source_id for t in _rows(store)}


# --- seed -> event (TP-V3-10) -------------------------------------------------------- #
def _session(client: TestClient) -> str:
    demo = _demo(client)
    out = client.post(
        f"/api/play/worlds/{demo['name']}/sessions",
        json={"name": "T", "start_region_id": demo["start_region_id"]},
    )
    return out.json()["session"]["id"]


def test_a_started_seed_reads_in_korean_on_the_next_events_read() -> None:
    client, _store = _app()
    _load(client)
    sid = _session(client)
    started = client.post(f"/api/gm/sessions/{sid}/seeds/seed-mushroom-blight/start")
    assert started.status_code == 201 and started.json()["description_ko"] is None  # a write
    (event,) = client.get(f"/api/gm/sessions/{sid}/events").json()
    assert (
        event["description_ko"]
        == "앰버메도의 버섯밭에 잿빛 반점이 번진다. 줄째로 불태워지고 수확이 불투명해진다."
    )


def test_without_a_matching_seed_row_or_with_a_failing_cache_the_start_still_stands() -> None:
    client, store = _app()
    _load(client)
    store.purge(kind="event_seed", ids=["seed-mushroom-blight"])  # e.g. the seed text was edited
    sid = _session(client)
    assert (
        client.post(f"/api/gm/sessions/{sid}/seeds/seed-mushroom-blight/start").status_code == 201
    )
    assert client.get(f"/api/gm/sessions/{sid}/events").json()[0]["description_ko"] is None

    class _ReadFails(InMemoryTranslationRepository):
        fail = False

        def get_many(self, keys, target_lang):
            if self.fail:
                raise RuntimeError("database down")
            return super().get_many(keys, target_lang)

    failing = _ReadFails()
    client, _ = _app(failing)
    _load(client)
    sid = _session(client)
    failing.fail = True
    assert client.post(f"/api/gm/sessions/{sid}/seeds/seed-sealed-relic/start").status_code == 201
