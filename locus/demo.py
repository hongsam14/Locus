"""Bundled demo fictional world for end-to-end validation (U9, Q5=A).

Same content is in examples/demo_world/. Run with: locus build-world --demo

When the bundled map image (examples/demo_world/map.png) is present it is included
so the build exercises the VLM ingestion path; otherwise it is omitted gracefully.
"""

from __future__ import annotations

from pathlib import Path

from .ingestion.service import WorldInputs

_MAP_IMAGE = Path(__file__).resolve().parents[1] / "examples" / "demo_world" / "map.png"

_DEMO_MEMO = """
The kingdom of Aldermoor spans two provinces split by the Spine Mountains.
- Riverton, a town in the Greenvale province, holds a market every Sunday by the
  Aldwen River; traders from the coast bring salt and rumors.
- Highcrag, a town beyond the Spine Mountains, is isolated; its people speak of
  Riverton's market only as a half-remembered legend.
- The sun rises in the east across all of Aldermoor.
- Mayor Tomas governs Riverton and is known for the river festival.
""".strip()

_DEMO_MAP = {
    "regions": [
        {"name": "Aldermoor", "level": "continent"},
        {"name": "Greenvale", "level": "province", "parent": "Aldermoor"},
        {"name": "Frostreach", "level": "province", "parent": "Aldermoor"},
        {"name": "Riverton", "level": "town", "parent": "Greenvale"},
        {"name": "Highcrag", "level": "town", "parent": "Frostreach"},
    ],
    "connections": [
        {"from": "Riverton", "to": "Highcrag", "kind": "blocked"},
    ],
}


def load_demo_world(include_map: bool = True) -> WorldInputs:
    """Return the bundled demo world inputs (memo + structured map [+ map image])."""
    map_images: list[bytes] = []
    if include_map and _MAP_IMAGE.exists():
        map_images.append(_MAP_IMAGE.read_bytes())
    return WorldInputs(memos=[_DEMO_MEMO], structured_maps=[_DEMO_MAP], map_images=map_images)
