"""Service-error → HTTP mapping shared by all routers.

LookupError → 404 · SessionClosedError / WorldExistsError / TurnInProgressError → 409 ·
ExecutorShutdownError / LlmUnavailableError → 503 ·
UnsupportedWorldFile → 422 · ValueError (incl. InvalidActionError) → 400. A missing
boundary is reported by ``api.deps`` as 503. ``PLAY_ERRORS`` is the except-tuple the
play / gm routers use (U4, code-plan R-03).
"""

from __future__ import annotations

from fastapi import HTTPException

from locus.play.base import SessionClosedError
from locus.play.errors import (
    ExecutorShutdownError,
    LlmCallFailedError,
    LlmUnavailableError,
    TurnInProgressError,
)
from locus.world.build import WorldExistsError
from locus.world.worldfile.schema import UnsupportedWorldFile

# Every service error a play / gm route turns into an HTTP status (U4).
PLAY_ERRORS: tuple[type[Exception], ...] = (
    LookupError,
    SessionClosedError,
    TurnInProgressError,
    ExecutorShutdownError,
    LlmUnavailableError,
    LlmCallFailedError,
    ValueError,
)


def http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (ExecutorShutdownError, LlmUnavailableError, LlmCallFailedError)):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, (SessionClosedError, WorldExistsError, TurnInProgressError)):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, UnsupportedWorldFile):  # before ValueError: it is a ValueError subclass
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    raise exc
