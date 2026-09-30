"""STATUS: in-progress — concept-art clues stay low-confidence entities and never become knowledge; image transport via API lands in U2.

Concept art ingestion via VLM (US-1.4, P1) — auxiliary low-confidence clues."""

from __future__ import annotations

from locus.shared.llm.base import LLMProvider, VLMProvider
from locus.shared.models import IngestionResult
from locus.world.ingestion.mapping import (
    CONCEPT_ART_CONFIDENCE_CAP,
    ingest_warning,
    merge_entities,
    to_entity,
)
from locus.world.ingestion.schemas import ArtExtraction

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
            return IngestionResult(
                world_id=world_id,
                warnings=[ingest_warning("empty concept art image", severity="error")],
            )
        try:
            description = self._vlm.analyze_image(image, _VLM_PROMPT)
            ex = self._llm.structured(description, ArtExtraction, system=_STRUCT_SYSTEM)
        except Exception as exc:  # graceful degrade
            return IngestionResult(
                world_id=world_id,
                warnings=[
                    ingest_warning(f"concept art extraction failed: {exc}", severity="error")
                ],
            )

        entities = []
        for clue in ex.clues:
            ent = to_entity(clue, world_id, generated_by="vlm")
            # cap confidence for auxiliary art clues (BR-U2-2)
            ent.confidence = min(ent.confidence, CONCEPT_ART_CONFIDENCE_CAP)
            entities.append(ent)
        entities, _ = merge_entities(entities)

        return IngestionResult(
            world_id=world_id,
            entities=entities,
            # all art clues are low-confidence hints
            low_confidence_item_ids=[e.id for e in entities],
        )
