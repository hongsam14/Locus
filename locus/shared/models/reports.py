"""Build / operation reports for Locus."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, computed_field

from locus.shared.models.graph import LocusModel


class BuildWarning(LocusModel):
    """A non-fatal issue surfaced during a build (graceful degradation)."""

    stage: str  # ingestion | topology | wiki | ontology | persist-graph | persist-search | embed | import | load
    item_id: str | None = None
    message: str
    # error = the build/import could not do what it promised (persist failure, an input
    # that could not be read at all, zero regions, broken references); warning = item-level
    # degradation the user should see (BR-U2-13)
    severity: Literal["warning", "error"] = "warning"


def has_errors(warnings: list["BuildWarning"]) -> bool:
    return any(w.severity == "error" for w in warnings)


class BuildReport(LocusModel):
    """Summary of a world (or wiki) build run."""

    world_id: str
    regions_created: int = 0
    connections_created: int = 0
    entities_created: int = 0
    knowledge_created: int = 0
    corroborations_created: int = 0
    warnings: list[BuildWarning] = Field(default_factory=list)
    unscoped_knowledge_ids: list[str] = Field(default_factory=list)  # RE A4
    llm_calls: int = 0  # LLM + VLM calls made by this build (NFR-5)
    embedding_calls: int = 0
    replaced: bool = False  # an existing world was deleted first (RE A3)
    closed_session_ids: list[str] = Field(default_factory=list)  # filled by the API/CLI layer
    backup_path: str | None = None  # pre-replace World File backup (BR-U2-11)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ok(self) -> bool:
        """No error-severity warning (BR-U2-13); warnings alone keep the build OK."""
        return not has_errors(self.warnings)

    @property
    def errors(self) -> list[BuildWarning]:
        return [w for w in self.warnings if w.severity == "error"]


class ImportReport(LocusModel):
    """Result of loading a World File into a world (U2 W9, BR-U2-4/5/11)."""

    world_id: str
    format_version: int
    source_world_id: str
    remapped: bool = False  # ids were rewritten (target != source, or forced)
    forced: bool = False
    replaced: bool = False
    backup_path: str | None = None
    closed_session_ids: list[str] = Field(default_factory=list)  # filled by the API/CLI layer
    counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[BuildWarning] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ok(self) -> bool:
        return not has_errors(self.warnings)

    @property
    def errors(self) -> list[BuildWarning]:
        return [w for w in self.warnings if w.severity == "error"]


class GraphSummary(LocusModel):
    """High-level counts for a world graph (authoring overview)."""

    world_id: str
    region_count: int = 0
    entity_count: int = 0
    knowledge_count: int = 0
    prior_count: int = 0
    region_ids: list[str] = Field(default_factory=list)
