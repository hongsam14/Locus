"""Concept art ingestion via VLM (US-1.4, P1) — auxiliary low-confidence clues."""

from __future__ import annotations

from ..llm.base import LLMProvider, VLMProvider
from ..models import IngestionResult
from .mapping import CONCEPT_ART_CONFIDENCE_CAP, merge_entities, to_entity
from .schemas import ArtExtraction

_VLM_PROMPT = "Describe the place, structures, and atmosphere depicted in this concept art."
_STRUCT_SYSTEM = (
    "From the concept-art description, list auxiliary clues as entities "
    "(place/object/custom) and an overall mood. These are low-confidence hints."
)


class ConceptArtIngestor:
    def __init__(self, vlm: VLMProvider, llm: LLMProvider) -> None:
        self._vlm = vlm
        self._llm = llm

    def extract(self, image: bytes, *, world_id: str) -> IngestionResult:
        if not image:
            return IngestionResult(world_id=world_id, errors=["empty concept art image"])
        try:
            description = self._vlm.analyze_image(image, _VLM_PROMPT)
            ex = self._llm.structured(description, ArtExtraction, system=_STRUCT_SYSTEM)
        except Exception as exc:  # graceful degrade
            return IngestionResult(
                world_id=world_id, errors=[f"concept art extraction failed: {exc}"]
            )

        entities = []
        for clue in ex.clues:
            ent = to_entity(clue, world_id, generated_by="vlm")
            # cap confidence for auxiliary art clues (BR-U2-2)
            ent.confidence = min(ent.confidence, CONCEPT_ART_CONFIDENCE_CAP)
            entities.append(ent)
        entities = merge_entities(entities)

        return IngestionResult(
            world_id=world_id,
            entities=entities,
            # all art clues are low-confidence hints
            low_confidence_item_ids=[e.id for e in entities],
        )
