"""RumorGenerator — LLM degree-chain distortion (S2, FR-R2).

Given a source statement and an ascending list of distortion degrees, produces
one ``SessionRumor`` per degree. Each step re-distorts the *previous step's
text* (text lineage, FR-R2.3/Q3=A); confidence decays as
``source_confidence * (1 - degree)`` (FR-R2.6). Graceful: if a step's LLM call
fails the chain stops there and the successful prefix is returned (NFR-R4).
"""

from __future__ import annotations

from ..llm.base import LLMProvider
from ..models import LocusModel, Provenance, SourceKind
from .models import SessionRumor

_SYSTEM = (
    "You distort a statement into a rumor. You are given the current text and a "
    "distortion strength in [0,1]: higher means further from the truth "
    "(0.2 minor detail changes, 0.5 exaggeration, 0.8 partial errors, 1.0 mostly "
    "fabricated). Keep it the same language and roughly the same length. Return "
    "only the distorted statement."
)


class RumorDraft(LocusModel):
    """Structured LLM output: the distorted statement for one degree step."""

    statement: str


class RumorGenerator:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def generate_chain(
        self,
        *,
        source_text: str,
        source_id: str,
        source_kind: str,
        source_confidence: float,
        region_id: str,
        session_id: str,
        degrees: list[float],
        birth_support: float = 0.0,
    ) -> list[SessionRumor]:
        """Build a chain of rumors, one per (ascending) degree. Graceful.

        ``birth_support`` seeds each new rumor's support so it survives a few quiet
        turns before decaying out (FD-H Q7=A / BR-H1-21); 0.0 keeps Phase 1/2
        behaviour for callers that construct the generator directly."""
        rumors: list[SessionRumor] = []
        prev_text = source_text
        prev_id = source_id
        prev_kind = source_kind
        for degree in degrees:
            try:
                draft = self._llm.structured(
                    self._prompt(prev_text, degree), RumorDraft, system=_SYSTEM
                )
            except Exception:
                # graceful: stop the chain; keep what succeeded (NFR-R4, BR-S2-7)
                break
            rumor = SessionRumor(
                session_id=session_id,
                region_id=region_id,
                distorted_from_id=prev_id,
                distorted_from_kind=prev_kind,
                statement=draft.statement,
                distortion_degree=degree,
                support=_clamp(birth_support),
                confidence=_clamp(source_confidence * (1.0 - degree)),
                promoted=False,
                provenance=Provenance(source=SourceKind.SESSION_RUMOR, generated_by="llm:rumor"),
            )
            rumors.append(rumor)
            # next step re-distorts this step's text (lineage, Q3=A)
            prev_text, prev_id, prev_kind = rumor.statement, rumor.id, "rumor"
        return rumors

    @staticmethod
    def _prompt(text: str, degree: float) -> str:
        return f"Distortion strength: {degree:.2f}\nText: {text}\n\nDistorted statement:"


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
