"""TranslationService cache-only-read + background-warm tests (X1, review #1/#3/#4)
+ PBT on source_hash. ``enrich`` returns a mapping and never mutates its inputs."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st
from pydantic import BaseModel

from locus.localization import TranslationService, source_hash
from locus.localization.storage.memory_repo import InMemoryTranslationRepository
from locus.localization.translator import Translator


class _CountingLLM:
    def __init__(self, *, echo: bool = False) -> None:
        self.echo = echo
        self.calls = 0

    def complete(self, prompt, *, system=None):
        self.calls += 1
        text = prompt.split("Text:\n", 1)[-1]
        return text if self.echo else "KO:" + text

    def structured(self, prompt, schema, *, system=None):  # pragma: no cover
        raise NotImplementedError


class _Item(BaseModel):
    id: str
    statement: str


def _svc(llm=None):
    store = InMemoryTranslationRepository()
    llm = llm or _CountingLLM()
    # default warm_scheduler=None -> inline warming (deterministic for tests)
    return TranslationService(store, Translator(llm)), llm, store


def test_read_is_cache_only_then_warm_populates() -> None:
    svc, llm, _ = _svc()
    it = _Item(id="r1", statement="hello")
    # first enrich: cache miss -> nothing for THIS response (review #3) ...
    assert svc.enrich([it], kind="rumor", fields=["statement"], session_id="s") == {}
    assert llm.calls == 1  # ... but a warm ran in the background (inline here)
    # second enrich: served from the warmed cache, no new LLM call
    out = svc.enrich([_Item(id="r1", statement="hello")], kind="rumor", fields=["statement"])
    assert out == {"r1": {"statement": "KO:hello"}}
    assert llm.calls == 1


def test_enrich_does_not_mutate_items() -> None:
    svc, _, _ = _svc()
    it = _Item(id="r1", statement="hello")
    svc.enrich([it], kind="rumor", fields=["statement"])
    svc.enrich([it], kind="rumor", fields=["statement"])
    assert it.model_dump() == {"id": "r1", "statement": "hello"}


def test_hash_change_retranslates() -> None:
    svc, llm, _ = _svc()
    svc.enrich([_Item(id="r1", statement="hello")], kind="rumor", fields=["statement"])
    svc.enrich([_Item(id="r1", statement="changed")], kind="rumor", fields=["statement"])
    assert llm.calls == 2  # source changed -> re-translate (BR-X1-6)


def test_self_identical_translation_is_cached() -> None:
    # echo=True -> ko == source; must still be cached so we don't re-hit the LLM (review #4)
    svc, llm, _ = _svc(_CountingLLM(echo=True))
    for _ in range(3):
        svc.enrich([_Item(id="r1", statement="Locus")], kind="rumor", fields=["statement"])
    assert llm.calls == 1


def test_enrich_is_fail_safe_on_store_error() -> None:
    class _BoomStore(InMemoryTranslationRepository):
        def get_many(self, keys, target_lang):
            raise RuntimeError("db down")

    svc = TranslationService(_BoomStore(), Translator(_CountingLLM()))
    # must not raise; degrades to "no translations" (review #1)
    assert svc.enrich([_Item(id="r1", statement="hello")], kind="rumor", fields=["statement"]) == {}


def test_configured_default_lang_is_used() -> None:
    store = InMemoryTranslationRepository()
    llm = _CountingLLM()
    svc = TranslationService(store, Translator(llm), default_lang="ja")
    svc.enrich([_Item(id="r1", statement="hello")], kind="rumor", fields=["statement"])
    assert store.get_many([("rumor", "r1", "statement")], "ja")  # review #2
    assert svc.default_lang == "ja"


@given(st.text())
def test_source_hash_is_stable_and_whitespace_normalized(text: str) -> None:
    assert source_hash(text) == source_hash(text)
    assert source_hash(text) == source_hash("  " + text.strip() + "  ")


def test_enrich_does_not_reschedule_misses_already_in_flight() -> None:
    scheduled = []
    service = TranslationService(
        InMemoryTranslationRepository(), Translator(_CountingLLM()), warm_scheduler=scheduled.append
    )
    item = _Item(id="r1", statement="hello")
    service.enrich([item], kind="rumor", fields=["statement"])
    service.enrich([item], kind="rumor", fields=["statement"])  # same miss, still warming
    assert len(scheduled) == 1
    scheduled[0]()  # warm completes -> key released, cache filled
    assert service.enrich([item], kind="rumor", fields=["statement"]) == {
        "r1": {"statement": "KO:hello"}
    }
    assert len(scheduled) == 1


def test_enrich_survives_a_dead_scheduler() -> None:
    def dead(_thunk):
        raise RuntimeError("cannot schedule new futures after shutdown")

    service = TranslationService(
        InMemoryTranslationRepository(), Translator(_CountingLLM()), warm_scheduler=dead
    )
    item = _Item(id="r1", statement="hello")
    assert service.enrich([item], kind="rumor", fields=["statement"]) == {}
    assert service.enrich([item], kind="rumor", fields=["statement"]) == {}  # key released
