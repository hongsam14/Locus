"""U1 LLM layer tests — retry behaviour + factory selection (mocked, no live calls)."""

from __future__ import annotations

import pytest

from locus.shared.config import Settings
from locus.shared.llm import MAX_ATTEMPTS, ProviderFactory, with_retry


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


# --- review U5 #3: the server's Retry-After is honoured, capped ----------------- #
class _Response:
    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = headers


class _StatusError(Exception):
    """Shaped like an SDK status error: it carries the HTTP response."""

    def __init__(self, headers: dict[str, str]) -> None:
        super().__init__("status")
        self.response = _Response(headers)


def _state(exc: BaseException, attempt: int = 1):
    from tenacity import RetryCallState, Retrying

    state = RetryCallState(Retrying(), None, (), {})
    state.attempt_number = attempt
    state.set_exception((type(exc), exc, None))
    return state


def test_review_3_retry_after_headers_are_read() -> None:
    from locus.shared.llm.retry import retry_after_seconds

    assert retry_after_seconds(_StatusError({"retry-after": "4"})) == 4.0
    assert retry_after_seconds(_StatusError({"retry-after-ms": "1500"})) == 1.5
    assert retry_after_seconds(_StatusError({"retry-after": "soon"})) is None
    assert retry_after_seconds(_StatusError({})) is None
    assert retry_after_seconds(RuntimeError("no response")) is None


def test_review_3_the_wait_follows_the_hint_within_the_cap() -> None:
    from locus.shared.llm.retry import RETRY_AFTER_CAP_SECONDS, retry_wait

    assert retry_wait(_state(_StatusError({"retry-after": "4"}))) == 4.0
    assert retry_wait(_state(_StatusError({"retry-after": "60"}))) == RETRY_AFTER_CAP_SECONDS
    # no hint: the exponential backoff (1s, then 2s)
    assert retry_wait(_state(RuntimeError("x"), attempt=1)) == 1.0
    assert retry_wait(_state(RuntimeError("x"), attempt=2)) == 2.0
    # a hint shorter than the backoff never shortens it
    assert retry_wait(_state(_StatusError({"retry-after": "0"}), attempt=2)) == 2.0
