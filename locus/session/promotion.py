"""PromotionPolicy — pure promote/demote evaluation (S2, FR-R3).

Given the session's rumors and a threshold, returns only the *transitions*:
rumors that should newly promote (support >= threshold, not yet promoted) and
rumors that should demote (support < threshold, currently promoted). Pure and
deterministic — PBT target (NFR-R5).
"""

from __future__ import annotations

from ..models import LocusModel
from .models import SessionRumor

DEFAULT_PROMOTION_THRESHOLD = 0.6


class PromotionResult(LocusModel):
    """Promotion transitions to apply this turn."""

    promoted_ids: list[str] = []
    demoted_ids: list[str] = []


def evaluate(
    rumors: list[SessionRumor], threshold: float = DEFAULT_PROMOTION_THRESHOLD
) -> PromotionResult:
    """Return promote/demote transitions (pure). Idempotent: already-promoted
    rumors still meeting the threshold yield no change (BR-S2-13)."""
    promoted = [r.id for r in rumors if r.support >= threshold and not r.promoted]
    demoted = [r.id for r in rumors if r.support < threshold and r.promoted]
    return PromotionResult(promoted_ids=promoted, demoted_ids=demoted)
