"""IngestionService: route multimodal inputs and merge into one IngestionResult (U2)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..llm.factory import ProviderFactory
from ..models import IngestionResult
from .concept_art_ingestor import ConceptArtIngestor
from .map_image_ingestor import MapImageIngestor
from .mapping import merge_entities, merge_regions
from .structured_map_ingestor import StructuredMapIngestor
from .text_ingestor import TextIngestor


class WorldInputs(BaseModel):
    """Raw multimodal inputs for a world build."""

    model_config = {"arbitrary_types_allowed": True}

    memos: list[str] = Field(default_factory=list)
    map_images: list[bytes] = Field(default_factory=list)
    structured_maps: list[dict] = Field(default_factory=list)
    concept_arts: list[bytes] = Field(default_factory=list)


def merge_results(world_id: str, results: list[IngestionResult]) -> IngestionResult:
    """Combine per-input results into one (dedup entities/regions)."""
    entities = merge_entities([e for r in results for e in r.entities])
    regions = merge_regions([rg for r in results for rg in r.region_hints])
    relations = [rel for r in results for rel in r.relations]
    knowledge = [k for r in results for k in r.knowledge]
    low = sorted({lc for r in results for lc in r.low_confidence_item_ids})
    errors = [e for r in results for e in r.errors]
    return IngestionResult(
        world_id=world_id,
        entities=entities,
        relations=relations,
        region_hints=regions,
        knowledge=knowledge,
        low_confidence_item_ids=low,
        errors=errors,
    )


class IngestionService:
    def __init__(
        self,
        text: TextIngestor,
        map_image: MapImageIngestor,
        structured_map: StructuredMapIngestor,
        concept_art: ConceptArtIngestor,
    ) -> None:
        self._text = text
        self._map_image = map_image
        self._structured_map = structured_map
        self._concept_art = concept_art

    @classmethod
    def from_factory(cls, factory: ProviderFactory) -> IngestionService:
        llm = factory.llm()
        vlm = factory.vlm()
        return cls(
            text=TextIngestor(llm),
            map_image=MapImageIngestor(vlm, llm),
            structured_map=StructuredMapIngestor(),
            concept_art=ConceptArtIngestor(vlm, llm),
        )

    def ingest_all(self, world_id: str, inputs: WorldInputs) -> IngestionResult:
        results: list[IngestionResult] = []
        for memo in inputs.memos:
            results.append(self._text.extract(memo, world_id=world_id))
        for img in inputs.map_images:
            results.append(self._map_image.extract(img, world_id=world_id))
        for doc in inputs.structured_maps:
            results.append(self._structured_map.parse(doc, world_id=world_id))
        for art in inputs.concept_arts:
            results.append(self._concept_art.extract(art, world_id=world_id))
        return merge_results(world_id, results)
