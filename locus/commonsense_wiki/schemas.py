"""LLM structured-output schemas for Wiki prior distillation (U6, Q3=A)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..models import PriorType


class PriorSuggestion(BaseModel):
    prior_type: PriorType = PriorType.FACT
    condition: str
    effect: str
    description: str | None = None
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class PriorBatch(BaseModel):
    items: list[PriorSuggestion] = Field(default_factory=list)
