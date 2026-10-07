"""Pure mapping/merge helpers: Extracted* -> U1 domain models (U2).

LLM-independent and therefore directly unit-testable / PBT-friendly (BR-U2-12).
"""

from __future__ import annotations

from locus.shared.models import (
    BuildWarning,
    Coord,
    Entity,
    Knowledge,
    Provenance,
    Region,
    RegionLevel,
    Relation,
    SourceKind,
    fallback_title,
)
from locus.shared.models.util import clamp01, normalize_name
from locus.world.ingestion.schemas import (
    ExtractedEntity,
    ExtractedKnowledge,
    ExtractedRegion,
    ExtractedRelation,
    ExtractedTerrain,
)

__all__ = [
    "CONCEPT_ART_CONFIDENCE_CAP",
    "LOW_CONFIDENCE_THRESHOLD",
    "EntityIdMap",
    "flag_low_confidence",
    "ingest_warning",
    "merge_entities",
    "merge_regions",
    "remap_entity_refs",
    "normalize_name",
    "to_entity",
    "to_knowledge",
    "to_region",
    "to_relation",
    "to_terrain_region",
]

LOW_CONFIDENCE_THRESHOLD = 0.5
CONCEPT_ART_CONFIDENCE_CAP = 0.4

EntityIdMap = dict[str, str]  # merged-away entity id -> canonical entity id (RE A2)
_LIST_ATTRS = ("adjacent_names", "connection_hints")  # merged as ordered unions (BR-U2-6)


def ingest_warning(
    message: str, *, severity: str = "warning", item_id: str | None = None
) -> BuildWarning:
    return BuildWarning(stage="ingestion", item_id=item_id, message=message, severity=severity)  # type: ignore[arg-type]


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


def to_region(x: ExtractedRegion, world_id: str, *, generated_by: str = "llm") -> Region:
    position = None
    if x.x is not None and x.y is not None:
        position = Coord(x=clamp01(x.x), y=clamp01(x.y))
    return Region(
        world_id=world_id,
        name=x.name,
        level=x.level,
        description=x.description,
        attributes={"parent_name": x.parent_name} if x.parent_name else {},
        position=position,
        provenance=_prov(generated_by),
    )


# terrain kinds that act as a connector/barrier BETWEEN regions (stay connection
# hints, not promoted to a Region) (FD-B Q1=B, BR-B1).
_BARRIER_KINDS = {
    "mountain",
    "mountains",
    "range",
    "sea",
    "ocean",
    "river",
    "road",
    "route",
    "bridge",
}


def is_barrier_terrain(kind: str) -> bool:
    return kind.strip().lower() in _BARRIER_KINDS


def to_terrain_region(x: ExtractedTerrain, world_id: str, *, generated_by: str = "vlm") -> Region:
    """Promote an area-form VLM terrain feature to a Region (FR-IM4.1, BR-B2)."""
    position = None
    if x.x is not None and x.y is not None:
        position = Coord(x=clamp01(x.x), y=clamp01(x.y))
    attributes: dict = {"terrain_kind": x.kind, "origin": "vlm"}
    if x.between:
        attributes["adjacent_names"] = list(x.between)
    return Region(
        world_id=world_id,
        name=x.name,
        level=RegionLevel.TERRAIN,
        description=x.note,
        attributes=attributes,
        position=position,
        provenance=_prov(generated_by),
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
        title=x.title or fallback_title(x.statement),
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
def merge_entities(entities: list[Entity]) -> tuple[list[Entity], EntityIdMap]:
    """Merge by (normalized name, entity_type); keep max confidence (BR-U2-4).

    Returns the canonical entities and the id map of merged-away ids so callers can
    re-point relations / ABOUT / LOCATED_IN (RE A2, BR-U2-7)."""
    merged: dict[tuple[str, str], Entity] = {}
    id_map: EntityIdMap = {}
    for e in entities:
        key = (normalize_name(e.name), str(e.entity_type))
        existing = merged.get(key)
        if existing is None:
            merged[key] = e
            continue
        id_map[e.id] = existing.id
        if e.confidence > existing.confidence:
            existing.confidence = e.confidence
        if not existing.description and e.description:
            existing.description = e.description
        if not existing.located_in and e.located_in:
            existing.located_in = e.located_in
    return list(merged.values()), id_map


def merge_regions(regions: list[Region]) -> tuple[list[Region], list[BuildWarning]]:
    """Merge region hints by (normalized name, level) (BR-U2-5).

    Attributes survive the merge (RE A1, BR-U2-6): list attributes (connection hints,
    adjacent names) become ordered unions, scalar attributes keep the first value and a
    differing later value is reported. ``description``/``position`` fill in when empty."""
    merged: dict[tuple[str, str], Region] = {}
    warnings: list[BuildWarning] = []
    for r in regions:
        key = (normalize_name(r.name), str(r.level))
        existing = merged.get(key)
        if existing is None:
            merged[key] = r
            continue
        if not existing.description and r.description:
            existing.description = r.description
        if existing.position is None and r.position is not None:
            existing.position = r.position
        for attr, val in r.attributes.items():
            if attr in _LIST_ATTRS and isinstance(val, list):
                cur = list(existing.attributes.get(attr, []) or [])
                for item in val:
                    if item not in cur:
                        cur.append(item)
                existing.attributes[attr] = cur
            elif attr not in existing.attributes:
                existing.attributes[attr] = val
            elif existing.attributes[attr] != val:
                warnings.append(
                    ingest_warning(
                        f"region '{existing.name}': attribute {attr!r} conflict "
                        f"({existing.attributes[attr]!r} kept, {val!r} dropped)",
                        item_id=existing.id,
                    )
                )
    return list(merged.values()), warnings


def remap_entity_refs(
    relations: list[Relation],
    knowledge: list[Knowledge],
    entities: list[Entity],
    id_map: EntityIdMap,
) -> tuple[list[Relation], list[Knowledge], list[BuildWarning]]:
    """Re-point relations / ABOUT ids onto canonical entity ids after a merge; drop
    relations whose endpoint is unknown even after remapping (BR-U2-7)."""
    known = {e.id for e in entities}
    warnings: list[BuildWarning] = []

    def canon(eid: str) -> str:
        return id_map.get(eid, eid)

    kept: list[Relation] = []
    for rel in relations:
        src, dst = canon(rel.source_id), canon(rel.target_id)
        if src not in known or dst not in known:
            warnings.append(
                ingest_warning(
                    f"relation {rel.relation_type!r} dropped: dangling reference "
                    f"({rel.source_id} -> {rel.target_id})",
                    item_id=rel.id,
                )
            )
            continue
        if (src, dst) != (rel.source_id, rel.target_id):
            rel = rel.model_copy(update={"source_id": src, "target_id": dst})
        kept.append(rel)
    out_k: list[Knowledge] = []
    for k in knowledge:
        ids = [canon(eid) for eid in k.about_entity_ids]
        ids = list(dict.fromkeys(eid for eid in ids if eid in known))
        out_k.append(
            k.model_copy(update={"about_entity_ids": ids}) if ids != k.about_entity_ids else k
        )
    return kept, out_k, warnings


def flag_low_confidence(*items, threshold: float = LOW_CONFIDENCE_THRESHOLD) -> list[str]:
    """Return ids of items whose confidence is below ``threshold`` (FR-A5)."""
    low: list[str] = []
    for group in items:
        for it in group:
            conf = getattr(it, "confidence", 1.0)
            if conf < threshold:
                low.append(it.id)
    return low
