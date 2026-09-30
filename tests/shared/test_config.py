"""U5 settings — dialogue knobs, display languages, and the provider retry pin (Step 2.4)."""

from __future__ import annotations

import sys
import types

import pytest
from pydantic import ValidationError

from locus.shared.config import Settings

_KEYS = (
    "NPC_MAX_FACTS",
    "NPC_MAX_RUMORS",
    "NPC_MAX_RECENT_MESSAGES",
    "NPC_MAX_MESSAGE_CHARS",
    "SUPPORTED_LANGS",
    "TRANSLATION_TARGET_LANG",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _KEYS:
        monkeypatch.delenv(key, raising=False)


def _settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_dialogue_knobs_default_and_load_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    t = _settings().play_tuning()
    assert (t.npc_max_facts, t.npc_max_rumors, t.npc_max_recent_messages) == (12, 8, 10)
    assert t.npc_max_message_chars == 500
    monkeypatch.setenv("NPC_MAX_FACTS", "3")
    monkeypatch.setenv("NPC_MAX_RUMORS", "0")
    monkeypatch.setenv("NPC_MAX_RECENT_MESSAGES", "4")
    monkeypatch.setenv("NPC_MAX_MESSAGE_CHARS", "80")
    t = _settings().play_tuning()
    assert (t.npc_max_facts, t.npc_max_rumors, t.npc_max_recent_messages) == (3, 0, 4)
    assert t.npc_max_message_chars == 80
    monkeypatch.setenv("NPC_MAX_MESSAGE_CHARS", "0")
    with pytest.raises(ValidationError):
        _settings()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ko,en", ("ko", "en")),  # the comma form that a tuple field would fail to decode
        (" KO , en ,", ("ko", "en")),
        ("", ("ko", "en")),  # empty falls back to the defaults
        ("ko", ("ko",)),
    ],
)
def test_supported_langs_parse_the_comma_form(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: tuple[str, ...]
) -> None:
    monkeypatch.setenv("SUPPORTED_LANGS", raw)
    assert _settings().supported_langs == expected


def test_the_default_display_language_must_be_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    """FD review R-04: a default outside the set would 400 every request without ?lang=."""
    monkeypatch.setenv("SUPPORTED_LANGS", "ko,en")
    monkeypatch.setenv("TRANSLATION_TARGET_LANG", "fr")
    with pytest.raises(ValidationError, match="not in SUPPORTED_LANGS"):
        _settings()
    monkeypatch.setenv("TRANSLATION_TARGET_LANG", "EN")  # case-insensitive
    assert _settings().translation_target_lang == "EN"


def test_both_providers_pin_sdk_retries_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """NFR review R-01: retries live only in `with_retry` (bounded; see retry.py)."""
    seen: list[dict] = []

    class RecordingChatOpenAI:
        def __init__(self, **kwargs) -> None:
            seen.append(kwargs)

    fake = types.ModuleType("langchain_openai")
    fake.ChatOpenAI = RecordingChatOpenAI  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "langchain_openai", fake)

    from locus.shared.llm.openai_provider import OpenAILLMProvider, OpenAIVLMProvider

    OpenAILLMProvider(api_key="k", model="m")
    OpenAIVLMProvider(api_key="k", model="m")
    assert [kw["max_retries"] for kw in seen] == [0, 0]
    assert all(kw["timeout"] == 30.0 for kw in seen)


def test_review_10_the_embedding_client_is_bounded_too(monkeypatch: pytest.MonkeyPatch) -> None:
    """Review U5 #10: the SDK default (2 retries, no timeout) stacked under with_retry."""
    seen: list[dict] = []

    class RecordingEmbeddings:
        def __init__(self, **kwargs) -> None:
            seen.append(kwargs)

    fake = types.ModuleType("langchain_openai")
    fake.OpenAIEmbeddings = RecordingEmbeddings  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "langchain_openai", fake)

    from locus.shared.llm.openai_provider import OpenAIEmbeddingProvider

    OpenAIEmbeddingProvider(api_key="k", model="m", dimension=8)
    assert seen[0]["max_retries"] == 0 and seen[0]["timeout"] == 30.0
