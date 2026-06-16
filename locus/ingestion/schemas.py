"""LLM/VLM structured-output schemas for ingestion (U2).

These are lightweight extraction DTOs the model fills in; ``mapping.py`` converts
them into U1 domain models (assigning ids + provenance).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..models import EntityType, RegionLevel


class ExtractedEntity(BaseModel):
    name: str
    entity_type: EntityType = EntityType.PLACE
    description: str | None = None
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class ExtractedRelation(BaseModel):
    source_name: str
    target_name: str
    relation_type: str
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class ExtractedRegion(BaseModel):
    name: str
    level: RegionLevel = RegionLevel.TOWN
    description: str | None = None
    parent_name: str | None = None
    # normalized map position (0=left/top .. 1=right/bottom); VLM may estimate these
    x: float | None = None
    y: float | None = None
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class ExtractedTerrain(BaseModel):
    name: str
    kind: str = "terrain"  # e.g. mountain, river, road, plain, forest, valley
    between: list[str] = Field(default_factory=list)  # region names it separates/links/borders
    note: str | None = None
    # normalized map position (0=left/top .. 1=right/bottom); VLM may estimate these (FD-B Q6=A)
    x: float | None = None
    y: float | None = None
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class ExtractedKnowledge(BaseModel):
    statement: str
    title: str | None = None  # short one-line title (FR-IM3.1/3.2)
    topic: str | None = None
    about_names: list[str] = Field(default_factory=list)
    region_name: str | None = None
    is_global: bool = False  # set True for world-wide facts (no specific region)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class TextExtraction(BaseModel):
    """Result of extracting structure from a free-text memo."""

    entities: list[ExtractedEntity] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)
    regions: list[ExtractedRegion] = Field(default_factory=list)
    knowledge: list[ExtractedKnowledge] = Field(default_factory=list)


class MapExtraction(BaseModel):
    """Result of interpreting a map image (VLM)."""

    regions: list[ExtractedRegion] = Field(default_factory=list)
    terrain: list[ExtractedTerrain] = Field(default_factory=list)
    connection_hints: list[ExtractedRelation] = Field(default_factory=list)


class ArtExtraction(BaseModel):
    """Result of interpreting concept art (auxiliary, low confidence)."""

    clues: list[ExtractedEntity] = Field(default_factory=list)
    mood: str | None = None
