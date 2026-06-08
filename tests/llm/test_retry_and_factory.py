"""U1 LLM layer tests — retry behaviour + factory selection (mocked, no live calls)."""

from __future__ import annotations

import pytest

from locus.config import Settings
from locus.llm import MAX_ATTEMPTS, ProviderFactory, with_retry


# --------------------------------------------------------------------------- #
# Retry policy
# --------------------------------------------------------------------------- #
def test_with_retry_succeeds_after_transient_failures() -> None:
    calls = {"n": 0}

    @with_retry
    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < MAX_ATTEMPTS:
            raise RuntimeError("transient")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == MAX_ATTEMPTS


def test_with_retry_reraises_after_max_attempts() -> None:
    calls = {"n": 0}

    @with_retry
    def always_fail() -> str:
        calls["n"] += 1
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        always_fail()
    assert calls["n"] == MAX_ATTEMPTS


# --------------------------------------------------------------------------- #
# Factory selection / errors (no langchain import on these paths)
# --------------------------------------------------------------------------- #
def _settings(**overrides) -> Settings:
    base = {
        "llm_provider": "openai",
        "openai_api_key": None,
        "neo4j_password": "x",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_factory_missing_openai_key_raises() -> None:
    factory = ProviderFactory(settings=_settings(openai_api_key=None))
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        factory.llm()


def test_factory_unsupported_provider_raises() -> None:
    factory = ProviderFactory(settings=_settings(llm_provider="acme"))
    with pytest.raises(ValueError, match="Unsupported llm_provider"):
        factory.embedding()
