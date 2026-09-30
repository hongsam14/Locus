"""Retry + timeout policy for external model calls (ND1-Q1=A).

3 attempts. Between attempts the wait is exponential (1s, then 2s) unless the server
said how long to wait: a ``Retry-After`` / ``retry-after-ms`` header on the error's
response (429 rate limits, 503) is honoured, capped at ``RETRY_AFTER_CAP_SECONDS``
(review U5 #3 — pinning the SDK's own retries off had dropped that hint). The
per-call timeout (30s) is configured on the client and the providers pin
``max_retries=0`` so the SDK does not retry underneath this layer.

Worst case per call: 30 × 3 + 8 + 8 = **106s** (two waits at the cap). The SDK timeout
applies per phase (connect, read), so this is the practical bound rather than a strict
one.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import TypeVar

from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

T = TypeVar("T")

MAX_ATTEMPTS = 3
CALL_TIMEOUT_SECONDS = 30.0
RETRY_AFTER_CAP_SECONDS = 8.0

_backoff = wait_exponential(multiplier=1, min=1, max=4)


def retry_after_seconds(exc: BaseException | None) -> float | None:
    """The server's wait hint on ``exc`` (an SDK status error carrying ``.response``)."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    try:
        millis = headers.get("retry-after-ms")
        if millis:
            return max(0.0, float(millis) / 1000.0)
        value = headers.get("retry-after")
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            when = parsedate_to_datetime(value)
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
    except (TypeError, ValueError, AttributeError):
        return None


def retry_wait(state: RetryCallState) -> float:
    base = float(_backoff(state))
    exc = state.outcome.exception() if state.outcome is not None else None
    hint = retry_after_seconds(exc)
    if hint is None:
        return base
    return min(max(base, hint), RETRY_AFTER_CAP_SECONDS)


def with_retry(fn: Callable[..., T]) -> Callable[..., T]:
    """Decorate a callable with 3 attempts; waits honour the server's Retry-After."""

    wrapped = retry(
        reraise=True,
        stop=stop_after_attempt(MAX_ATTEMPTS),
        wait=retry_wait,
        retry=retry_if_exception_type(Exception),
    )(fn)
    return wrapped
