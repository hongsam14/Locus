"""play boundary error types raised by the player-mode services (U4).

``InvalidActionError`` is a ``ValueError`` (HTTP 400 via ``api.errors``);
``TurnInProgressError`` maps to 409 (BR-U4-13).
"""

from __future__ import annotations


class InvalidActionError(ValueError):
    """The action cannot be performed from the player's current state (BR-U4-6/7)."""


class TurnInProgressError(RuntimeError):
    """A turn run is already in progress for this session (BR-U4-13)."""


class ExecutorShutdownError(RuntimeError):
    """The background turn executor is shut down, so no new run can start (503).

    Raised instead of a bare ``RuntimeError`` so the API maps it to 503 rather than
    letting it escape as an unhandled 500 (code review U4-2 #14).
    """


class LlmUnavailableError(RuntimeError):
    """A method that needs an LLM provider was called without one (503).

    The deterministic parts of a service stay usable: gating the whole service on the
    provider 503'd seven routes that never touch an LLM (code review U4-2 #13).
    """


class ConversationExistsError(ValueError):
    """A conversation for this session and NPC already exists (UNIQUE session_id, npc_id).

    A dedicated type so the concurrent-first-message recovery in ``say`` does not
    swallow unrelated ``ValueError`` s (U5 plan review R-03).
    """


class AppraisalExistsError(ValueError):
    """An NPC already judged this deed (``UNIQUE (deed_id, npc_id)``, BR-U6-10). Only a
    write outside the turn guard (CLI, a second worker) can hit it."""
