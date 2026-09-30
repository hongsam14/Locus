"""Map image ingestion via VLM (US-1.2)."""

from __future__ import annotations

from locus.shared.llm.base import LLMProvider, VLMProvider
from locus.shared.models import BuildWarning, IngestionResult
from locus.world.ingestion.mapping import (
    ingest_warning,
    is_barrier_terrain,
    merge_regions,
    to_region,
    to_terrain_region,
)
from locus.world.ingestion.schemas import MapExtraction

_VLM_PROMPT = (
    "Describe this world map: name the labelled regions, their relative layout, and "
    "terrain features (mountains, rivers, roads) that separate or link regions."
)
_STRUCT_SYSTEM = (
    "From the map description, extract regions, terrain features (with the regions they "
    "lie between), and connection hints. For each region, ESTIMATE its relative position "
    "on the map as normalized x,y in [0,1] (x: 0=left .. 1=right, y: 0=top .. 1=bottom). "
    "Provide confidence in [0,1] per item."
)

# terrain kind -> connection kind (consumed by U3 topology)
_TERRAIN_TO_KIND = {
    "mountain": "blocked",
    "range": "blocked",
    "mountains": "blocked",
    "sea": "blocked",
    "ocean": "blocked",
    "desert": "blocked",
    "river": "river",
    "road": "route",
    "route": "route",
    "bridge": "route",
}


class MapImageIngestor:
    def __init__(self, vlm: VLMProvider, llm: LLMProvider) -> None:
        self._vlm = vlm
        self._llm = llm

    def extract(self, image: bytes, *, world_id: str) -> IngestionResult:
        if not image:
            return IngestionResult(
                world_id=world_id, warnings=[ingest_warning("empty map image", severity="error")]
            )
        try:
            description = self._vlm.analyze_image(image, _VLM_PROMPT)
            ex = self._llm.structured(description, MapExtraction, system=_STRUCT_SYSTEM)
        except Exception as exc:  # graceful degrade
            return IngestionResult(
                world_id=world_id,
                warnings=[ingest_warning(f"map extraction failed: {exc}", severity="error")],
            )

        regions = [to_region(r, world_id, generated_by="vlm") for r in ex.regions]

        # Terrain classification (FD-B Q1=B, BR-B1):
        #  - barrier/connector kinds -> A-B connection hint only (no node)
        #  - area-form kinds -> promote to a Region(level=TERRAIN), join topology
        hints: list[dict] = [
            {"from": c.source_name, "to": c.target_name, "kind": "route"}
            for c in ex.connection_hints
        ]
        warnings: list[BuildWarning] = []
        for t in ex.terrain:
            if is_barrier_terrain(t.kind):
                if len(t.between) == 2:
                    hints.append(
                        {
                            "from": t.between[0],
                            "to": t.between[1],
                            "kind": _TERRAIN_TO_KIND.get(t.kind.strip().lower(), "adjacent"),
                            "terrain_kind": t.kind,
                        }
                    )
                else:
                    # barrier connects exactly two regions (FD-B Q1=B); anything else
                    # is surfaced instead of silently dropped (FR-H8 / BR-H2-3).
                    warnings.append(
                        ingest_warning(
                            f"barrier terrain '{t.name}' ({t.kind}) skipped: expected 2 "
                            f"bordering regions, got {len(t.between)}"
                        )
                    )
            else:
                # area terrain -> promoted Region; connect it to each bordering region
                region = to_terrain_region(t, world_id)
                regions.append(region)
                for neighbor in t.between:
                    hints.append({"from": t.name, "to": neighbor, "kind": "adjacent"})

        regions, merge_warnings = merge_regions(regions)
        if hints and regions:
            regions[0].attributes.setdefault("connection_hints", hints)

        return IngestionResult(
            world_id=world_id, region_hints=regions, warnings=warnings + merge_warnings
        )
