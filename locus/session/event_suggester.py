"""EventSuggester — LLM event proposals (Phase 2 / P2, FR-P2.2).

Given the session state (regions, current turn), proposes candidate events as
``EventDraft`` objects. These are *uncommitted* — the GameMasterService persists
them as SUGGESTED for the suggest-then-approve gate (CL2.1/2.2). Graceful: any
LLM failure yields an empty list so the turn/session keeps going (NFR-P3).
"""

from __future__ import annotations

from pydantic import Field

from ..llm.base import LLMProvider
from ..models import LocusModel
from .models import EventCategory

_SYSTEM = (
    "You are a game master proposing events that could plausibly affect regions "
    "of a fantasy world during a play-through. Each event targets one region and "
    "has a category (war, plague, politics, disaster, festival, discovery), a short "
    "description, and a magnitude in [0,1] (how strongly it shakes local rumor/"
    "truth). Propose grounded, varied events. Return only the requested structure."
)


class EventDraft(LocusModel):
    """An uncommitted LLM event proposal (FR-P2.2)."""

    region_id: str
    category: EventCategory
    description: str = ""
    magnitude: float = Field(ge=0.0, le=1.0)


class EventDraftList(LocusModel):
    """Structured LLM output: a batch of proposals."""

    drafts: list[EventDraft] = Field(default_factory=list)


class EventSuggester:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def suggest(
        self,
        *,
        world_id: str,
        region_ids: list[str],
        turn: int,
        context: str = "",
        n: int = 1,
    ) -> list[EventDraft]:
        """Propose up to ``n`` events for the session. Graceful: [] on failure."""
        if not region_ids:
            return []
        try:
            result = self._llm.structured(
                self._prompt(region_ids, turn, context, n), EventDraftList, system=_SYSTEM
            )
        except Exception:
            return []  # graceful (NFR-P3, BR-P2-11)
        return result.drafts[:n]

    @staticmethod
    def _prompt(region_ids: list[str], turn: int, context: str, n: int) -> str:
        regions = ", ".join(region_ids)
        ctx = f"\nContext: {context}" if context else ""
        return (
            f"Turn: {turn}\nRegions (use these ids as region_id): {regions}{ctx}\n\n"
            f"Propose up to {n} event(s)."
        )
