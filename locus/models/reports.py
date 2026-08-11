"""Build / operation reports for Locus."""

from __future__ import annotations

from pydantic import Field

from .graph import LocusModel


class BuildWarning(LocusModel):
    """A non-fatal issue surfaced during a build (graceful degradation)."""

    stage: str  # e.g. "ingestion", "topology", "ontology", "consensus"
    item_id: str | None = None
    message: str


class BuildReport(LocusModel):
    """Summary of a world (or wiki) build run."""

    world_id: str
    regions_created: int = 0
    connections_created: int = 0
    entities_created: int = 0
    knowledge_created: int = 0
    corroborations_created: int = 0
    warnings: list[BuildWarning] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        """A build is OK even with warnings; warnings are informational."""
        return True


class WikiBuildReport(LocusModel):
    """Summary of a Common-sense Wiki (real-world digital twin) build."""

    world_id: str
    regions: int = 0
    entities: int = 0
    knowledge: int = 0
    priors: int = 0
    warnings: list[BuildWarning] = Field(default_factory=list)


class GraphSummary(LocusModel):
    """High-level counts for a world graph (authoring overview)."""

    world_id: str
    region_count: int = 0
    entity_count: int = 0
    knowledge_count: int = 0
    prior_count: int = 0
    region_ids: list[str] = Field(default_factory=list)
