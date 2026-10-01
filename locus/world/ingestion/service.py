"""IngestionService: route multimodal inputs and merge into one IngestionResult (U2)."""

from __future__ import annotations

import base64
import binascii
from typing import Annotated

from pydantic import BaseModel, Field

from locus.shared.llm.base import LLMProvider, VLMProvider
from locus.shared.llm.factory import ProviderFactory
from locus.shared.models import IngestionResult
from locus.world.ingestion.concept_art_ingestor import ConceptArtIngestor
from locus.world.ingestion.map_image_ingestor import MapImageIngestor
from locus.world.ingestion.mapping import (
    ingest_warning,
    merge_entities,
    merge_regions,
    remap_entity_refs,
)
from locus.world.ingestion.structured_map_ingestor import StructuredMapIngestor
from locus.world.ingestion.text_ingestor import TextIngestor

# Input caps (U3 review S19): the multipart route's per-field limits (``api/uploads.py``
# reads these) also bound the JSON body, so both paths cap a build's LLM calls alike.
MEMOS_MAX, MEMO_CHARS = 20, 60_000
MAPS_MAX = 5
MAP_IMAGES_MAX, CONCEPT_ARTS_MAX = 4, 8
IMAGE_B64_CHARS = 8 * 1024 * 1024 * 4 // 3 + 4  # an 8 MiB image as base64


class WorldInputs(BaseModel):
    """Raw multimodal inputs for a world build."""

    model_config = {"arbitrary_types_allowed": True}

    memos: list[Annotated[str, Field(max_length=MEMO_CHARS)]] = Field(
        default_factory=list, max_length=MEMOS_MAX
    )
    map_images: list[Annotated[str, Field(max_length=IMAGE_B64_CHARS)]] = Field(
        default_factory=list, max_length=MAP_IMAGES_MAX
    )  # base64-encoded images (RE A7)
    structured_maps: list[dict] = Field(default_factory=list, max_length=MAPS_MAX)
    concept_arts: list[Annotated[str, Field(max_length=IMAGE_B64_CHARS)]] = Field(
        default_factory=list, max_length=CONCEPT_ARTS_MAX
    )  # base64-encoded images
    name: str | None = None  # WorldMeta (U2)
    description: str | None = None


def merge_results(world_id: str, results: list[IngestionResult]) -> IngestionResult:
    """Combine per-input results into one: dedup entities/regions across inputs and
    re-point every entity reference onto the canonical ids (RE A1/A2, BR-U2-6/7)."""
    entities, id_map = merge_entities([e for r in results for e in r.entities])
    regions, region_warnings = merge_regions([rg for r in results for rg in r.region_hints])
    relations, knowledge, ref_warnings = remap_entity_refs(
        [rel for r in results for rel in r.relations],
        [k for r in results for k in r.knowledge],
        entities,
        id_map,
    )
    low = sorted({id_map.get(lc, lc) for r in results for lc in r.low_confidence_item_ids})
    warnings = [w for r in results for w in r.warnings] + region_warnings + ref_warnings
    return IngestionResult(
        world_id=world_id,
        entities=entities,
        relations=relations,
        region_hints=regions,
        knowledge=knowledge,
        low_confidence_item_ids=low,
        warnings=warnings,
        entity_id_map=id_map,
    )


def decode_image(value: str, *, what: str) -> tuple[bytes | None, str | None]:
    """base64 -> bytes; returns (None, reason) for input that is not valid base64."""
    try:
        data = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        return None, f"{what} is not valid base64: {exc}"
    if not data:
        return None, f"{what} is empty"
    return data, None


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
        return cls.from_providers(factory.llm(), factory.vlm())

    @classmethod
    def from_providers(cls, llm: LLMProvider, vlm: VLMProvider) -> IngestionService:
        """Build with explicit providers (the builder passes per-build counting wrappers)."""
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
        for i, img in enumerate(inputs.map_images):
            data, reason = decode_image(img, what=f"map image #{i}")
            if data is None:
                results.append(_unreadable(world_id, reason))  # BR-U2-10
                continue
            results.append(self._map_image.extract(data, world_id=world_id))
        for doc in inputs.structured_maps:
            results.append(self._structured_map.parse(doc, world_id=world_id))
        for i, art in enumerate(inputs.concept_arts):
            data, reason = decode_image(art, what=f"concept art #{i}")
            if data is None:
                results.append(_unreadable(world_id, reason))
                continue
            results.append(self._concept_art.extract(data, world_id=world_id))
        return merge_results(world_id, results)


def _unreadable(world_id: str, reason: str | None) -> IngestionResult:
    return IngestionResult(
        world_id=world_id, warnings=[ingest_warning(reason or "unreadable input", severity="error")]
    )
