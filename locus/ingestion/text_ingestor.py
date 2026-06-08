"""Text memo ingestion (US-1.1)."""

from __future__ import annotations

from ..llm.base import LLMProvider
from ..models import IngestionResult
from .mapping import (
    flag_low_confidence,
    merge_entities,
    merge_regions,
    normalize_name,
    to_entity,
    to_knowledge,
    to_region,
    to_relation,
)
from .schemas import TextExtraction

_SYSTEM = (
    "You extract structured world-building knowledge from a designer's free-text note. "
    "Identify entities (place/person/event/object/custom), their relations, region "
    "mentions, and stand-alone knowledge statements. Provide a confidence in [0,1] for "
    "each item reflecting how clearly it is stated."
)


class TextIngestor:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def extract(self, memo: str, *, world_id: str) -> IngestionResult:
        if not memo or not memo.strip():
            return IngestionResult(world_id=world_id, errors=["empty memo"])
        try:
            ex = self._llm.structured(memo, TextExtraction, system=_SYSTEM)
        except Exception as exc:  # graceful degrade (BR-U2-10)
            return IngestionResult(world_id=world_id, errors=[f"text extraction failed: {exc}"])

        entities = merge_entities([to_entity(x, world_id) for x in ex.entities])
        regions = merge_regions([to_region(x, world_id) for x in ex.regions])

        name_to_id = {normalize_name(e.name): e.id for e in entities}
        # resolve ABOUT here (about_names + entities are both local to this extraction)
        knowledge = [
            to_knowledge(
                x,
                world_id,
                about_entity_ids=[
                    name_to_id[normalize_name(n)]
                    for n in x.about_names
                    if normalize_name(n) in name_to_id
                ],
            )
            for x in ex.knowledge
        ]

        relations = []
        for x in ex.relations:
            rel = to_relation(x, world_id, name_to_id)
            if rel is not None:
                relations.append(rel)

        return IngestionResult(
            world_id=world_id,
            entities=entities,
            relations=relations,
            region_hints=regions,
            knowledge=knowledge,
            low_confidence_item_ids=flag_low_confidence(entities, knowledge),
        )
