"""Service-error → HTTP mapping shared by all routers.

Every error body is ``{"detail": …, "code": …}`` (V2, FR-D9): the screens pick a user
sentence by ``code`` and keep ``detail`` for the folded original. ``ERROR_CODES`` is an
ordered list — the first ``isinstance`` match wins, so a subclass sits above its base
(``UnsupportedWorldFile`` above ``ValueError``, the augmentation conflicts above
``AugmentationConflict``). A service error the table does not name is re-raised and
becomes a 500. ``PLAY_ERRORS`` is the except-tuple the play / gm routers use (U4,
code-plan R-03). ``RegionInUseError`` is not in the table: the editor router raises it
with an object ``detail`` (its ``session_ids``) that a string would lose.
"""

from __future__ import annotations

from fastapi import HTTPException

from locus.play.base import SessionClosedError
from locus.play.errors import (
    AppraisalExistsError,
    ConversationExistsError,
    ExecutorShutdownError,
    InvalidActionError,
    LlmCallFailedError,
    LlmUnavailableError,
    SeedAlreadyRunningError,
    TurnInProgressError,
)
from locus.world.augmentation.types import (
    AugmentationConflict,
    ChangeAlreadyRevertedError,
    RevertConflictError,
    RevertOrderError,
    RunFinishedError,
)
from locus.world.build import BuildInProgressError, WorldExistsError
from locus.world.worldfile.schema import UnsupportedWorldFile


class ApiError(HTTPException):
    """An ``HTTPException`` that carries the error ``code`` of its body."""

    def __init__(
        self,
        status_code: int,
        detail: object,
        code: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code


# Ordered: the first match wins (V2 domain-entities § 5).
ERROR_CODES: list[tuple[type[Exception], int, str]] = [
    (SessionClosedError, 409, "session_closed"),
    (TurnInProgressError, 409, "turn_running"),
    (SeedAlreadyRunningError, 409, "seed_running"),
    (WorldExistsError, 409, "world_exists"),
    (BuildInProgressError, 409, "build_running"),
    (RunFinishedError, 409, "run_finished"),
    (ChangeAlreadyRevertedError, 409, "change_reverted"),
    (RevertOrderError, 409, "revert_order"),
    (RevertConflictError, 409, "revert_conflict"),
    (AugmentationConflict, 409, "augmentation_conflict"),
    (ExecutorShutdownError, 503, "shutting_down"),
    (LlmUnavailableError, 503, "llm_unavailable"),
    (LlmCallFailedError, 503, "llm_failed"),
    (UnsupportedWorldFile, 422, "unsupported_world_file"),
    (InvalidActionError, 400, "invalid_action"),
    (ConversationExistsError, 400, "conversation_exists"),
    (AppraisalExistsError, 400, "appraisal_exists"),
    (LookupError, 404, "not_found"),
    (ValueError, 400, "invalid_request"),
]

# The code of an error body that names none (a plain HTTPException, a route 404/405).
DEFAULT_CODES: dict[int, str] = {
    400: "invalid_request",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "too_large",
    422: "validation_failed",
    500: "error",
    503: "service_unavailable",
}

# Every service error a play / gm route turns into an HTTP status (U4).
PLAY_ERRORS: tuple[type[Exception], ...] = (
    LookupError,
    SessionClosedError,
    TurnInProgressError,
    ExecutorShutdownError,
    LlmUnavailableError,
    LlmCallFailedError,
    SeedAlreadyRunningError,
    ValueError,
)


def code_for(status_code: int) -> str:
    """The default ``code`` of a status that came without one."""
    return DEFAULT_CODES.get(status_code, "error")


def http_error(exc: Exception) -> ApiError:
    for kind, status, code in ERROR_CODES:
        if isinstance(exc, kind):
            return ApiError(status, str(exc), code)
    raise exc
