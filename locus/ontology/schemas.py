"""LLM structured-output schemas for U4 ontology (corroboration + dedup)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CorroborationSuggestion(BaseModel):
    """An LLM-proposed corroborating fact for a region (FR-C3, Q3=B)."""

    statement: str
    title: str | None = None  # short one-line title (FR-IM3.1)
    topic: str | None = None
    rationale: str = ""
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)


class CorroborationBatch(BaseModel):
    items: list[CorroborationSuggestion] = Field(default_factory=list)


class DuplicateVerdict(BaseModel):
    """LLM judgment on whether two knowledge statements are duplicates (CL2=C)."""

    is_duplicate: bool
    reason: str = ""


class EntityMatchVerdict(BaseModel):
    """LLM judgment on whether a VLM entity is the same as an existing one (FD-B Q3=A)."""

    same_entity: bool = False
    canonical_name: str | None = None


class RegionPickVerdict(BaseModel):
    """LLM choice of the region an orphan entity is located in (FD-B Q4=A)."""

    region_name: str | None = None  # None -> cannot place
