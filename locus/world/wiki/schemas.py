"""LLM structured-output schemas for Wiki prior distillation + linking, and the wiki tab's
reference views (U3, domain-entities §5)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from locus.shared.models import PriorType, WikiDomain, WikiPrior
from locus.shared.models.graph import LocusModel
from locus.world.refs import ConnectionKey, NameRef


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


# --------------------------------------------------------------------------- #
# Reference views (U3, Q4=A, US-2.8)
# --------------------------------------------------------------------------- #
class PriorRefView(LocusModel):
    """The prior a connection cites; ``broken`` when the world has no such prior."""

    prior_id: str
    condition: str | None = None
    effect: str | None = None
    broken: bool = False


class PriorUsage(LocusModel):
    """One wiki-tab row: a stored prior and what cites it."""

    prior: WikiPrior
    connections: list[ConnectionKey] = Field(default_factory=list)
    knowledge: list[NameRef] = Field(default_factory=list)


class BrokenRef(LocusModel):
    """A cited prior id the world does not hold ("저장되지 않은 근거")."""

    ref_id: str
    connections: list[ConnectionKey] = Field(default_factory=list)
    knowledge: list[NameRef] = Field(default_factory=list)
