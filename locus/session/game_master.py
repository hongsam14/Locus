"""GameMasterService — per-turn session coordinator (S2 + Phase 2).

Thin coordinator over four single-responsibility services, each injected (and
default-constructed from the shared repo/loader when not supplied):

- ``RumorService``      — generate / regenerate rumors, adjust support
- ``EventService``      — event lifecycle (create / resolve / discard / suggest / approve)
- ``DistortionService`` — per-region distortion read / write
- ``TurnAdvancer``      — the advance_turn sequence (composes the above)

The public method surface is unchanged (routers/tests depend on it); this class
now just delegates. Canonical access stays read-only throughout (NFR-R2).
"""

from __future__ import annotations

from ..consensus.engine import DEFAULT_PARAMS, ConsensusParams
from ..query.loader import WorldLoader
from .base import SessionClosedError
from .distortion_service import DistortionService
from .event_service import EventService
from .event_suggester import EventSuggester
from .models import (
    EventCategory,
    EventLifecycle,
    RegionDistortion,
    SessionEvent,
    SessionRumor,
)
from .repository import SessionRepository
from .rumor_dynamics import DEFAULT_RUMOR_DYNAMICS, RumorDynamicsParams
from .rumor_feedback_service import RumorFeedbackService
from .rumor_generator import RumorGenerator
from .rumor_service import RumorService
from .turn import TurnAdvancer, TurnResult

__all__ = ["GameMasterService", "SessionClosedError", "TurnResult"]


class GameMasterService:
    def __init__(
        self,
        repo: SessionRepository,
        generator: RumorGenerator,
        loader: WorldLoader,
        params: ConsensusParams = DEFAULT_PARAMS,
        *,
        suggester: EventSuggester | None = None,
        rumor_params: RumorDynamicsParams = DEFAULT_RUMOR_DYNAMICS,
        rumors: RumorService | None = None,
        events: EventService | None = None,
        distortions: DistortionService | None = None,
        feedback: RumorFeedbackService | None = None,
        turns: TurnAdvancer | None = None,
    ) -> None:
        self._repo = repo
        self._rumors = rumors or RumorService(
            repo, generator, loader, params, birth_support=rumor_params.birth_support
        )
        self._events = events or EventService(repo, loader, suggester=suggester)
        self._distortions = distortions or DistortionService(repo)
        self._feedback = feedback or RumorFeedbackService(repo, rumor_params)
        self._turns = turns or TurnAdvancer(
            repo, loader, self._rumors, self._feedback, rumor_params
        )

    # -- reads ------------------------------------------------------------ #
    def list_rumors(self, session_id: str, region_id: str) -> list[SessionRumor]:
        return self._rumors.list_rumors(session_id, region_id)

    def list_events(self, session_id: str, *, status: str | None = None) -> list[SessionEvent]:
        return self._events.list_events(session_id, status=status)

    def list_distortions(self, session_id: str) -> list[RegionDistortion]:
        return self._distortions.list_distortions(session_id)

    # -- events (EventService) ------------------------------------------- #
    def create_event(
        self,
        session_id: str,
        region_id: str,
        *,
        category: EventCategory,
        magnitude: float,
        description: str = "",
        lifecycle: EventLifecycle | None = None,
    ) -> SessionEvent:
        return self._events.create_event(
            session_id,
            region_id,
            category=category,
            magnitude=magnitude,
            description=description,
            lifecycle=lifecycle,
        )

    def resolve_event(self, session_id: str, event_id: str) -> SessionEvent:
        return self._events.resolve_event(session_id, event_id)

    def discard_event(self, session_id: str, event_id: str) -> None:
        self._events.discard_event(session_id, event_id)

    def suggest_events(self, session_id: str, *, n: int = 1) -> list[SessionEvent]:
        return self._events.suggest_events(session_id, n=n)

    def approve_event(self, session_id: str, event_id: str) -> SessionEvent:
        return self._events.approve_event(session_id, event_id)

    # -- rumors (RumorService) ------------------------------------------- #
    def generate_rumors(
        self, session_id: str, region_id: str, *, degrees: list[float] | None = None
    ) -> list[SessionRumor]:
        return self._rumors.generate_rumors(session_id, region_id, degrees=degrees)

    def regenerate_region(self, session_id: str, region_id: str) -> list[SessionRumor]:
        return self._rumors.regenerate_region(session_id, region_id)

    def adjust_support(self, session_id: str, rumor_id: str, support: float) -> SessionRumor:
        return self._rumors.adjust_support(session_id, rumor_id, support)

    # -- distortion (DistortionService) ---------------------------------- #
    def set_region_distortion(self, session_id: str, region_id: str, degree: float) -> None:
        self._distortions.set_region_distortion(session_id, region_id, degree)

    # -- turn (TurnAdvancer) --------------------------------------------- #
    def advance_turn(self, session_id: str, **kwargs) -> TurnResult:
        return self._turns.advance_turn(session_id, **kwargs)
