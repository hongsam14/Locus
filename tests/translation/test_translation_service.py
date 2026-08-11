"""TranslationService cache-only-read + background-warm tests (X1, review #1/#3/#4)
+ PBT on source_hash."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st
from pydantic import BaseModel

from locus.session.memory_repo import InMemorySessionRepository
from locus.translation import TranslationService, source_hash
from locus.translation.translator import Translator


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
    statement_ko: str | None = None


def _svc(llm=None):
    repo = InMemorySessionRepository()
    llm = llm or _CountingLLM()
    # default warm_scheduler=None -> inline warming (deterministic for tests)
    return TranslationService(repo, Translator(llm)), llm, repo


def test_read_is_cache_only_then_warm_populates() -> None:
    svc, llm, _ = _svc()
    it = _Item(id="r1", statement="hello")
    # first enrich: cache miss -> ko stays None on THIS response (review #3)
    svc.enrich([it], kind="rumor", fields=[("statement", "statement_ko")], session_id="s")
    assert it.statement_ko is None
    assert llm.calls == 1  # but a warm ran in the background (inline here)
    # second enrich: served from the warmed cache, no new LLM call
    it2 = _Item(id="r1", statement="hello")
    svc.enrich([it2], kind="rumor", fields=[("statement", "statement_ko")], session_id="s")
    assert it2.statement_ko == "KO:hello"
    assert llm.calls == 1


def test_hash_change_retranslates() -> None:
    svc, llm, _ = _svc()
    a = _Item(id="r1", statement="hello")
    svc.enrich([a], kind="rumor", fields=[("statement", "statement_ko")], session_id="s")
    b = _Item(id="r1", statement="changed")
    svc.enrich([b], kind="rumor", fields=[("statement", "statement_ko")], session_id="s")
    assert llm.calls == 2  # source changed -> re-translate (BR-X1-6)


def test_self_identical_translation_is_cached() -> None:
    # echo=True -> ko == source; must still be cached so we don't re-hit the LLM (review #4)
    svc, llm, _ = _svc(_CountingLLM(echo=True))
    for _ in range(3):
        it = _Item(id="r1", statement="Locus")
        svc.enrich([it], kind="rumor", fields=[("statement", "statement_ko")], session_id="s")
    assert llm.calls == 1


def test_enrich_is_fail_safe_on_repo_error() -> None:
    class _BoomRepo(InMemorySessionRepository):
        def get_translations_many(self, keys, target_lang):
            raise RuntimeError("db down")

    svc = TranslationService(_BoomRepo(), Translator(_CountingLLM()))
    it = _Item(id="r1", statement="hello")
    # must not raise; degrades to original (review #1)
    svc.enrich([it], kind="rumor", fields=[("statement", "statement_ko")], session_id="s")
    assert it.statement_ko is None


def test_configured_default_lang_is_used() -> None:
    repo = InMemorySessionRepository()
    llm = _CountingLLM()
    svc = TranslationService(repo, Translator(llm), default_lang="ja")
    it = _Item(id="r1", statement="hello")
    svc.enrich([it], kind="rumor", fields=[("statement", "statement_ko")], session_id="s")
    assert repo.get_translation("rumor", "r1", "statement", "ja") is not None  # review #2


@given(st.text())
def test_source_hash_is_stable_and_whitespace_normalized(text: str) -> None:
    assert source_hash(text) == source_hash(text)
    assert source_hash(text) == source_hash("  " + text.strip() + "  ")
