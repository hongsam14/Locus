"""Retry + timeout policy for external model calls (ND1-Q1=A).

3 attempts with exponential backoff between them (waits 1s, then 2s — three
attempts mean two waits). The per-call timeout (30s) is configured on the client and
the providers pin ``max_retries=0`` so the SDK does not retry underneath this layer.
Worst case per call: 30 × 3 + 1 + 2 = **93s**. The SDK timeout applies per phase
(connect, read), so this is the practical bound rather than a strict one.
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
