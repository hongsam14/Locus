"""Values the world editor reads and returns (U3, domain-entities §2)."""

from __future__ import annotations

from pydantic import Field

from locus.shared.models import NPC, Knowledge, Region
from locus.shared.models.graph import LocusModel
from locus.world.refs import ConnectionKey, NameRef
from locus.world.wiki.schemas import PriorRefView

__all__ = [
    "ConnectionKey",
    "ConnectionView",
    "EditorRegionView",
    "NameRef",
    "RegionDeletePlan",
    "RegionDeleteReport",
    "RegionInUseError",
    "ScopedKnowledge",
    "WorldSummary",
]


class RegionDeletePlan(LocusModel):
    """What deleting a region will do (Q1=A, BR-U3-9); shown before the delete."""

    region_id: str
    region_name: str
    new_parent_id: str | None = None  # where the children move (the deleted region's parent)
    children: list[NameRef] = Field(default_factory=list)
    connections: list[ConnectionKey] = Field(default_factory=list)
    npcs: list[NameRef] = Field(default_factory=list)
    knowledge_to_unscope: list[NameRef] = Field(default_factory=list)
    knowledge_scope_removed: list[NameRef] = Field(default_factory=list)
    entities_unlocated: list[NameRef] = Field(default_factory=list)
    seed_ids: list[str] = Field(default_factory=list)  # U8 (BR-U8-14): its event seeds go too
    blocked_by_sessions: list[str] = Field(default_factory=list)  # Q2=A, filled by the router


class RegionDeleteReport(RegionDeletePlan):
    """The same shape after the delete, plus the node ids removed (region, NPCs, seeds)."""

    deleted_ids: list[str] = Field(default_factory=list)
    seeds_deleted: int = 0


class ConnectionView(LocusModel):
    key: ConnectionKey
    other_region_id: str
    other_region_name: str
    weight: float
    rationale: str | None = None
    prior: PriorRefView | None = None  # Q4=A: the cited prior, or a broken ref


class ScopedKnowledge(LocusModel):
    knowledge: Knowledge
    scope_region_ids: list[str] = Field(default_factory=list)  # every region it is scoped to


class EditorRegionView(LocusModel):
    """One region as the editor opens it (originals, not a consensus view)."""

    region: Region
    children: list[NameRef] = Field(default_factory=list)
    connections: list[ConnectionView] = Field(default_factory=list)  # leaving this region
    knowledge: list[ScopedKnowledge] = Field(default_factory=list)  # DIRECT here
    npcs: list[NPC] = Field(default_factory=list)


class WorldSummary(LocusModel):
    id: str
    name: str
    description: str | None = None
    region_count: int = 0
    updated_at: str | None = None
    last_writer: str | None = None


class RegionInUseError(RuntimeError):
    """A player of an open session stands in the region (Q2=A) -> 409."""

    def __init__(self, region_id: str, session_ids: list[str]) -> None:
        super().__init__(
            f"region {region_id} is in use by open session(s): {', '.join(session_ids)}"
        )
        self.region_id = region_id
        self.session_ids = list(session_ids)
