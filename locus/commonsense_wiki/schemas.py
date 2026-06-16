"""LLM structured-output schemas for Wiki prior distillation + linking."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..models import PriorType, WikiDomain


class PriorSuggestion(BaseModel):
    prior_type: PriorType = PriorType.FACT
    condition: str
    effect: str
    domains: list[WikiDomain] = Field(default_factory=list)  # shared taxonomy (FR-IM2.1)
    description: str | None = None
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class PriorBatch(BaseModel):
    items: list[PriorSuggestion] = Field(default_factory=list)


class PriorLinkVerdict(BaseModel):
    """LLM judgment on whether two WikiPriors are related (FR-IM2.4)."""

    related: bool = False
    relation: str = "related"  # label, e.g. "reinforces" / "implies" / "contrasts"
    weight: float = Field(default=0.5, ge=0.0, le=1.0)
