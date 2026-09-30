"""Retry + timeout policy for external model calls (ND1-Q1=A).

3 attempts, exponential backoff (1s -> 2s -> 4s). The per-call timeout is
configured on the underlying client (LangChain ``request_timeout``); here we
own the retry/backoff concern so all providers share it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

T = TypeVar("T")

MAX_ATTEMPTS = 3
CALL_TIMEOUT_SECONDS = 30.0


def with_retry(fn: Callable[..., T]) -> Callable[..., T]:
    """Decorate a callable with 3x exponential-backoff retry on any Exception."""

    wrapped = retry(
        reraise=True,
        stop=stop_after_attempt(MAX_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(Exception),
    )(fn)
    return wrapped
