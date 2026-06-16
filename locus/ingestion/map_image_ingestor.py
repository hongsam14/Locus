"""Map image ingestion via VLM (US-1.2)."""

from __future__ import annotations

from ..llm.base import LLMProvider, VLMProvider
from ..models import IngestionResult
from .mapping import is_barrier_terrain, merge_regions, to_region, to_terrain_region
from .schemas import MapExtraction

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
            return IngestionResult(world_id=world_id, errors=["empty map image"])
        try:
            description = self._vlm.analyze_image(image, _VLM_PROMPT)
            ex = self._llm.structured(description, MapExtraction, system=_STRUCT_SYSTEM)
        except Exception as exc:  # graceful degrade
            return IngestionResult(world_id=world_id, errors=[f"map extraction failed: {exc}"])

        regions = [to_region(r, world_id, generated_by="vlm") for r in ex.regions]

        # Terrain classification (FD-B Q1=B, BR-B1):
        #  - barrier/connector kinds -> A-B connection hint only (no node)
        #  - area-form kinds -> promote to a Region(level=TERRAIN), join topology
        hints: list[dict] = [
            {"from": c.source_name, "to": c.target_name, "kind": "route"}
            for c in ex.connection_hints
        ]
        for t in ex.terrain:
            if is_barrier_terrain(t.kind) and len(t.between) == 2:
                hints.append(
                    {
                        "from": t.between[0],
                        "to": t.between[1],
                        "kind": _TERRAIN_TO_KIND.get(t.kind.strip().lower(), "adjacent"),
                        "terrain_kind": t.kind,
                    }
                )
            elif not is_barrier_terrain(t.kind):
                # area terrain -> promoted Region; connect it to each bordering region
                region = to_terrain_region(t, world_id)
                regions.append(region)
                for neighbor in t.between:
                    hints.append({"from": t.name, "to": neighbor, "kind": "adjacent"})

        regions = merge_regions(regions)
        if hints and regions:
            regions[0].attributes.setdefault("connection_hints", hints)

        return IngestionResult(world_id=world_id, region_hints=regions)
