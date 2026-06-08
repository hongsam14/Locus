"""Pure mapping/merge helpers: Extracted* -> U1 domain models (U2).

LLM-independent and therefore directly unit-testable / PBT-friendly (BR-U2-12).
"""

from __future__ import annotations

import re

from ..models import (
    Coord,
    Entity,
    EntityType,
    Knowledge,
    Provenance,
    Region,
    Relation,
    SourceKind,
)
from .schemas import (
    ExtractedEntity,
    ExtractedKnowledge,
    ExtractedRegion,
    ExtractedRelation,
    ExtractedTerrain,
)

LOW_CONFIDENCE_THRESHOLD = 0.5
CONCEPT_ART_CONFIDENCE_CAP = 0.4

_WS_RE = re.compile(r"\s+")


def normalize_name(name: str) -> str:
    """Lowercase + collapse whitespace for dedup keys (BR-U2-4)."""
    return _WS_RE.sub(" ", name.strip().lower())


def _prov(generated_by: str) -> Provenance:
    return Provenance(source=SourceKind.INPUT, generated_by=generated_by)


# --------------------------------------------------------------------------- #
# Extracted -> domain
# --------------------------------------------------------------------------- #
def to_entity(x: ExtractedEntity, world_id: str, *, generated_by: str = "llm") -> Entity:
    return Entity(
        world_id=world_id,
        name=x.name,
        entity_type=x.entity_type,
        description=x.description,
        confidence=x.confidence,
        provenance=_prov(generated_by),
    )


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def to_region(x: ExtractedRegion, world_id: str, *, generated_by: str = "llm") -> Region:
    position = None
    if x.x is not None and x.y is not None:
        position = Coord(x=_clamp01(x.x), y=_clamp01(x.y))
    return Region(
        world_id=world_id,
        name=x.name,
        level=x.level,
        description=x.description,
        attributes={"parent_name": x.parent_name} if x.parent_name else {},
        position=position,
        provenance=_prov(generated_by),
    )


def to_terrain_entity(x: ExtractedTerrain, world_id: str, *, generated_by: str = "vlm") -> Entity:
    return Entity(
        world_id=world_id,
        name=x.name,
        entity_type=EntityType.TERRAIN,
        description=x.note,
        confidence=x.confidence,
        provenance=Provenance(
            source=SourceKind.INPUT,
            generated_by=generated_by,
            note=f"between={x.between}" if x.between else None,
        ),
    )


def to_relation(
    x: ExtractedRelation,
    world_id: str,
    name_to_id: dict[str, str],
    *,
    generated_by: str = "llm",
) -> Relation | None:
    src = name_to_id.get(normalize_name(x.source_name))
    tgt = name_to_id.get(normalize_name(x.target_name))
    if src is None or tgt is None:
        return None
    return Relation(
        world_id=world_id,
        source_id=src,
        target_id=tgt,
        relation_type=x.relation_type,
        confidence=x.confidence,
        provenance=_prov(generated_by),
    )


def to_knowledge(
    x: ExtractedKnowledge,
    world_id: str,
    *,
    about_entity_ids: list[str] | None = None,
    generated_by: str = "llm",
) -> Knowledge:
    return Knowledge(
        world_id=world_id,
        statement=x.statement,
        topic=x.topic,
        is_global=x.is_global,
        region_hint=x.region_name,
        about_entity_ids=about_entity_ids or [],
        confidence=x.confidence,
        provenance=_prov(generated_by),
    )


# --------------------------------------------------------------------------- #
# Merge / flag
# --------------------------------------------------------------------------- #
def merge_entities(entities: list[Entity]) -> list[Entity]:
    """Merge by (normalized name, entity_type); keep max confidence (BR-U2-4)."""
    merged: dict[tuple[str, str], Entity] = {}
    for e in entities:
        key = (normalize_name(e.name), str(e.entity_type))
        existing = merged.get(key)
        if existing is None:
            merged[key] = e
            continue
        if e.confidence > existing.confidence:
            existing.confidence = e.confidence
        if not existing.description and e.description:
            existing.description = e.description
    return list(merged.values())


def merge_regions(regions: list[Region]) -> list[Region]:
    """Merge region hints by (normalized name, level) (BR-U2-5)."""
    merged: dict[tuple[str, str], Region] = {}
    for r in regions:
        key = (normalize_name(r.name), str(r.level))
        if key not in merged:
            merged[key] = r
        elif not merged[key].description and r.description:
            merged[key].description = r.description
    return list(merged.values())


def flag_low_confidence(*items, threshold: float = LOW_CONFIDENCE_THRESHOLD) -> list[str]:
    """Return ids of items whose confidence is below ``threshold`` (FR-A5)."""
    low: list[str] = []
    for group in items:
        for it in group:
            conf = getattr(it, "confidence", 1.0)
            if conf < threshold:
                low.append(it.id)
    return low
