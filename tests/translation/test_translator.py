"""Translator unit tests (X1 / BR-X1-1..4, review #4)."""

from __future__ import annotations

from locus.translation import Translator


class _LLM:
    def __init__(self, *, fail: bool = False, echo: bool = True) -> None:
        self.fail = fail
        self.echo = echo
        self.calls = 0

    def complete(self, prompt, *, system=None):
        self.calls += 1
        if self.fail:
            raise RuntimeError("boom")
        text = prompt.split("Text:\n", 1)[-1]
        return text if self.echo else "KO:" + text

    def structured(self, prompt, schema, *, system=None):  # pragma: no cover
        raise NotImplementedError


def test_try_translate_happy_path() -> None:
    assert Translator(_LLM(echo=False)).try_translate("hello") == "KO:hello"


def test_blank_returns_none_without_llm_call() -> None:
    llm = _LLM()
    assert Translator(llm).try_translate("   ") is None  # BR-X1-1
    assert llm.calls == 0


def test_llm_failure_returns_none() -> None:
    # None signals failure so the caller does not cache and retries later (review #4)
    assert Translator(_LLM(fail=True)).try_translate("keep me") is None


def test_self_identical_translation_is_returned_not_none() -> None:
    # Proper nouns/numbers may translate to themselves; that is a success (cacheable),
    # distinct from a failure (review #4).
    assert Translator(_LLM(echo=True)).try_translate("Locus") == "Locus"
