"""U5 dialogue API + display language + translation purge over HTTP (Step 6.5)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from locus.localization import TranslationService
from locus.localization.models import Translation
from locus.localization.storage.memory_repo import InMemoryTranslationRepository
from locus.localization.translator import Translator
from locus.localization.wiring import LocalizationContainer
from locus.play import InMemoryPlayRepository
from locus.play.rumor.generator import RumorGenerator
from locus.shared.models import (
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
from tests.api.play_fixtures import DialogueLLM, RumorLLM
from tests.play.helpers import compose_play
from tests.play.strategies import npc
from tests.shared.snapshots import snapshot_of


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


class _World:
    """Riverton (a) with Mara; Hollow (b, not connected) with Bo; one fact in a."""

    def __init__(self) -> None:
        a = Region(world_id="w", name="Riverton", level=RegionLevel.TOWN, provenance=_prov())
        a.id = "a"
        b = Region(world_id="w", name="Hollow", level=RegionLevel.TOWN, provenance=_prov())
        b.id = "b"
        k = Knowledge(
            world_id="w", statement="The market burned.", title="fire", provenance=_prov()
        )
        k.id = "k-fire"
        self._kg = KnowledgeGraph(
            world_id="w",
            knowledge=[k],
            scopes=[
                ScopeLink(
                    world_id="w", knowledge_id=k.id, region_id="a", scope_type=ScopeType.DIRECT
                )
            ],
        )
        self._topo = RegionTopology(world_id="w", regions=[a, b])
        self._npcs = [npc("n1", "a", name="Mara"), npc("n2", "b", name="Bo")]

    def get(self, world_id):
        if world_id != "w":
            raise LookupError(f"world not found: {world_id}")
        return snapshot_of(self._kg, self._topo, npcs=self._npcs)


class _TranslatorLLM(RumorLLM):
    def __init__(self) -> None:
        self.completions = 0

    def complete(self, prompt, *, system=None):
        self.completions += 1
        return super().complete(prompt, system=system)


def _app(*, dialogue_llm=None, no_llm: bool = False, localized: bool = False):
    repo = InMemoryPlayRepository()
    llm = None if no_llm else (dialogue_llm or DialogueLLM())
    play = compose_play(repo, RumorGenerator(RumorLLM()), _World(), dialogue_llm=llm)
    loc = None
    translator = None
    if localized:
        translator = _TranslatorLLM()
        loc = LocalizationContainer(
            translations=TranslationService(InMemoryTranslationRepository(), Translator(translator))
        )
    client = TestClient(create_app(play=play, localization=loc))
    return client, play, llm, loc, translator


def _start(client: TestClient) -> str:
    r = client.post("/api/play/worlds/w/sessions", json={"name": "Ari", "start_region_id": "a"})
    assert r.status_code == 201, r.text
    return r.json()["session"]["id"]


def test_npcs_start_say_history_round_trip() -> None:
    client, _play, llm, _loc, _t = _app()
    sid = _start(client)
    npcs = client.get(f"/api/play/sessions/{sid}/npcs").json()
    assert [(n["npc"]["id"], n["has_conversation"], n["message_count"]) for n in npcs] == [
        ("n1", False, 0)
    ]
    first = client.post(f"/api/play/sessions/{sid}/npcs/n1/start")
    assert first.status_code == 200 and first.json()["messages"] == []
    assert client.post(f"/api/play/sessions/{sid}/npcs/n1/start").json()["id"] == first.json()["id"]
    reply = client.post(f"/api/play/sessions/{sid}/npcs/n1/say", json={"text": "What happened?"})
    assert reply.status_code == 200, reply.text
    body = reply.json()
    assert body["message"]["role"] == "npc" and body["llm_calls"] == 1 and body["lang"] == "ko"
    assert "k-fire" in body["context_ids"]
    assert len(llm.calls) == 1  # TP-U5-5
    history = client.get(f"/api/play/sessions/{sid}/npcs/n1/history").json()
    assert [m["role"] for m in history["messages"]] == ["player", "npc"]
    assert client.get(f"/api/play/sessions/{sid}/npcs").json()[0]["message_count"] == 2
    assert client.get(f"/api/play/sessions/{sid}/npcs/n2/history").status_code == 404


def test_ex11_status_codes() -> None:
    client, _play, _llm, _loc, _t = _app()
    sid = _start(client)

    def say(npc_id: str, text: str):
        return client.post(f"/api/play/sessions/{sid}/npcs/{npc_id}/say", json={"text": text})

    assert say("n2", "hi").status_code == 400  # lives in Hollow
    assert say("ghost", "hi").status_code == 404  # not in this world
    assert say("n1", "   ").status_code == 400
    assert say("n1", "x" * 501).status_code == 400
    assert client.post(f"/api/play/sessions/{sid}/npcs/n1/say", json={}).status_code == 422
    client.post(f"/api/play/sessions/{sid}/close")
    assert say("n1", "hi").status_code == 409


def test_without_a_provider_start_works_and_say_is_503() -> None:
    client, _play, _llm, _loc, _t = _app(no_llm=True)
    sid = _start(client)
    assert client.post(f"/api/play/sessions/{sid}/npcs/n1/start").status_code == 200
    r = client.post(f"/api/play/sessions/{sid}/npcs/n1/say", json={"text": "hi"})
    assert r.status_code == 503 and "LLM" in r.json()["detail"]


def test_dialogue_is_allowed_while_a_turn_holds_the_session() -> None:
    client, play, _llm, _loc, _t = _app()
    sid = _start(client)
    play.guard.acquire(sid, "run-x")
    try:
        assert (
            client.post(f"/api/play/sessions/{sid}/npcs/n1/say", json={"text": "hi"}).status_code
            == 200
        )
        assert client.post(f"/api/gm/sessions/{sid}/advance").status_code == 409
    finally:
        play.guard.release(sid)


@pytest.mark.parametrize(
    "path",
    [
        "/api/play/sessions/{sid}/region",
        "/api/play/sessions/{sid}/regions/a/knowledge",
        "/api/gm/sessions/{sid}/regions/a/rumors",
        "/api/gm/sessions/{sid}/events",
        "/api/knowledge/worlds/w/regions/a",
    ],
)
def test_tp_u5_8_an_unsupported_lang_is_400_on_every_lang_route(path: str) -> None:
    client, _play, _llm, loc, translator = _app(localized=True)
    sid = _start(client)
    r = client.get(path.format(sid=sid), params={"lang": "fr"})
    assert r.status_code == 400 and "unsupported lang" in r.json()["detail"]
    assert translator.completions == 0  # never became a cache key


def test_tp_u5_8_say_rejects_an_unsupported_lang_and_honours_en() -> None:
    client, _play, llm, _loc, _t = _app()
    sid = _start(client)
    bad = client.post(
        f"/api/play/sessions/{sid}/npcs/n1/say", params={"lang": "fr"}, json={"text": "hi"}
    )
    assert bad.status_code == 400 and llm.calls == []
    ok = client.post(
        f"/api/play/sessions/{sid}/npcs/n1/say", params={"lang": "EN"}, json={"text": "hi"}
    )
    assert ok.status_code == 200 and ok.json()["lang"] == "en"
    assert "English" in llm.calls[-1][1]


def test_lang_en_returns_originals_and_warms_nothing() -> None:
    client, _play, _llm, _loc, translator = _app(localized=True)
    sid = _start(client)
    view = client.get(f"/api/play/sessions/{sid}/region", params={"lang": "en"}).json()
    assert view["facts"] and all(f["statement_ko"] is None for f in view["facts"])
    assert translator.completions == 0  # BR-U5-19: no en→en warm
    client.get(f"/api/play/sessions/{sid}/region")  # default ko: the cache warms
    assert translator.completions >= 1


def test_the_timeline_takes_no_lang() -> None:
    """FD R-04(2): the timeline carries no translated field; the parameter is not declared."""
    client, _play, _llm, _loc, _t = _app()
    sid = _start(client)
    assert client.get(f"/api/gm/sessions/{sid}/timeline", params={"lang": "fr"}).status_code == 200


def test_ex9_regenerate_purges_the_replaced_rumors_translations() -> None:
    client, play, _llm, loc, _t = _app(localized=True)
    sid = _start(client)
    first = client.post(f"/api/gm/sessions/{sid}/regions/a/rumors").json()
    assert first
    store = loc.translations._store
    store.upsert_many(
        [
            Translation(
                source_kind="rumor",
                source_id=r["id"],
                source_field="statement",
                text="번역",
                source_hash="h",
                session_id=sid,
            )
            for r in first
        ]
        + [
            Translation(
                source_kind="knowledge",
                source_id="k-fire",
                source_field="statement",
                text="시장이 불탔다",
                source_hash="h",
                world_id="w",
            )
        ]
    )
    regen = client.post(f"/api/gm/sessions/{sid}/regions/a/rumors/regen")
    assert regen.status_code == 200
    gone = store.get_many([("rumor", r["id"], "statement") for r in first], "ko")
    assert gone == {}  # the replaced rumors' translations went with them
    kept = store.get_many([("knowledge", "k-fire", "statement")], "ko")
    assert kept  # unrelated rows stay


def test_regenerate_without_localization_still_works() -> None:
    client, _play, _llm, _loc, _t = _app(localized=False)
    sid = _start(client)
    client.post(f"/api/gm/sessions/{sid}/regions/a/rumors")
    assert client.post(f"/api/gm/sessions/{sid}/regions/a/rumors/regen").status_code == 200
