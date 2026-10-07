"""Localization at the API layer (FR-A2/G2): responses carry ``*_ko`` from the
localization container; domain services know nothing about translation."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from locus.localization import (
    InMemoryTranslationRepository,
    LocalizationContainer,
    TranslationService,
    Translator,
)
from tests.api.play_fixtures import RumorLLM, play_container


class CountingLLM(RumorLLM):
    def __init__(self) -> None:
        self.completions = 0

    def complete(self, prompt, *, system=None):
        self.completions += 1
        return super().complete(prompt, system=system)


def _client(*, localized: bool = True, llm: RumorLLM | None = None) -> TestClient:
    loc = None
    if localized:
        # default warm_scheduler=None -> inline warming (deterministic for tests)
        service = TranslationService(InMemoryTranslationRepository(), Translator(llm or RumorLLM()))
        loc = LocalizationContainer(translations=service)
    return TestClient(create_app(play=play_container(), localization=loc))


def _start(client: TestClient) -> str:
    return client.post("/api/play/worlds/w/sessions").json()["id"]


def test_generate_null_then_cached_read_localizes() -> None:
    client = _client()
    sid = _start(client)
    gen = client.post(f"/api/gm/sessions/{sid}/regions/r1/rumors").json()
    assert gen and all(r["statement_ko"] is None for r in gen)  # generate is lazy

    # Reads are cache-only: first read is a miss (null) but warms the cache
    # inline (test scheduler); the next read serves the translation.
    client.get(f"/api/gm/sessions/{sid}/regions/r1/rumors")
    listed = client.get(f"/api/gm/sessions/{sid}/regions/r1/rumors").json()
    assert listed and all(r["statement_ko"] == "KO:distorted" for r in listed)


def test_session_knowledge_is_localized_after_warm() -> None:
    client = _client()
    sid = _start(client)
    client.post(f"/api/gm/sessions/{sid}/regions/r1/rumors")  # seed a rumor
    client.get(f"/api/play/sessions/{sid}/regions/r1/knowledge")  # warm
    res = client.get(f"/api/play/sessions/{sid}/regions/r1/knowledge").json()
    items = res["items"]
    canon = [it for it in items if not (it.get("source") or "").startswith("rumor")]
    rumor = [it for it in items if (it.get("source") or "").startswith("rumor")]
    assert canon and canon[0]["statement_ko"] == "KO:fact"
    assert rumor and rumor[0]["statement_ko"] == "KO:distorted"


def test_advance_includes_region_changes() -> None:
    client = _client()
    sid = _start(client)
    res = client.post(f"/api/gm/sessions/{sid}/advance").json()
    assert "region_changes" in res and isinstance(res["region_changes"], list)


def test_translation_disabled_shows_original() -> None:
    # No localization container -> ko stays null (graceful, originals shown).
    client = _client(localized=False)
    sid = _start(client)
    client.post(f"/api/gm/sessions/{sid}/regions/r1/rumors")
    listed = client.get(f"/api/gm/sessions/{sid}/regions/r1/rumors").json()
    assert listed and all(r["statement_ko"] is None for r in listed)


def test_gm_writes_never_call_the_translator() -> None:
    # X1 Q2=A: write paths return ko=null and schedule nothing (review U1 #5)
    llm = CountingLLM()
    client = _client(llm=llm)
    sid = _start(client)
    gen = client.post(f"/api/gm/sessions/{sid}/regions/r1/rumors").json()
    client.put(f"/api/gm/sessions/{sid}/rumors/{gen[0]['id']}/support", json={"support": 0.9})
    client.post(f"/api/gm/sessions/{sid}/regions/r1/rumors/regen")
    assert llm.completions == 0
    client.get(f"/api/gm/sessions/{sid}/regions/r1/rumors")  # first read warms once per item
    first = llm.completions
    assert first > 0
    client.get(f"/api/gm/sessions/{sid}/regions/r1/rumors")  # cached now
    assert llm.completions == first
