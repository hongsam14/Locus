"""Bundled demo worlds (U2 W10, FR-B3, US-1.3).

``DemoWorlds`` lists and loads the World Files shipped inside the package
(``worlds/manifest.json``); loading goes through ``WorldFileImporter`` and makes
**no LLM call** (BR-U2-28). The pre-U2 source-based demo (memo + structured map
[+ map image for the VLM]) stays available as ``build_from_sources`` /
``load_demo_world`` for development builds that exercise the LLM pipeline.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from locus.shared.models import BuildReport, ImportReport
from locus.world.ingestion.service import WorldInputs
from locus.world.worldfile.import_ import WorldFileImporter
from locus.world.worldfile.schema import WorldFile

if TYPE_CHECKING:  # pragma: no cover
    from locus.world.build import WorldBuilder

_HERE = Path(__file__).resolve().parent
WORLDS_DIR = _HERE / "worlds"  # packaged (pyproject package-data)
# locus/world/demo/__init__.py -> parents[3] is the repository root (examples/ is not packaged)
_MAP_IMAGE = _HERE.parents[2] / "examples" / "demo_world" / "map.png"

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


class DemoInfo(BaseModel):
    name: str
    title: str
    description: str | None = None
    file: str


def load_demo_world(include_map: bool = True) -> WorldInputs:
    """Source inputs of the Aldermoor demo (memo + structured map [+ map image])."""
    map_images: list[str] = []
    if include_map and _MAP_IMAGE.exists():
        map_images.append(base64.b64encode(_MAP_IMAGE.read_bytes()).decode("ascii"))
    return WorldInputs(
        memos=[_DEMO_MEMO],
        structured_maps=[_DEMO_MAP],
        map_images=map_images,
        name="Aldermoor",
        description="Demo world built from its sources",
    )


class DemoWorlds:
    def __init__(
        self,
        importer: WorldFileImporter,
        builder: WorldBuilder | None = None,
        *,
        worlds_dir: Path = WORLDS_DIR,
    ) -> None:
        self._importer = importer
        self._builder = builder
        self._dir = worlds_dir

    def list(self) -> list[DemoInfo]:
        raw = json.loads((self._dir / "manifest.json").read_text(encoding="utf-8"))
        return [DemoInfo.model_validate(item) for item in raw]

    def info(self, name: str) -> DemoInfo:
        for item in self.list():
            if item.name == name:
                return item
        raise LookupError(f"demo world not found: {name}")

    def load_file(self, name: str) -> WorldFile:
        path = self._dir / self.info(name).file
        return WorldFile.parse(json.loads(path.read_text(encoding="utf-8")))

    def load(self, name: str, world_id: str, *, replace: bool = True) -> ImportReport:
        """Import the packaged World File into ``world_id`` — LLM-free (BR-U2-28)."""
        return self._importer.import_(world_id, self.load_file(name), replace=replace)

    def build_from_sources(
        self, name: str, world_id: str, *, replace: bool = True, include_map: bool = True
    ) -> BuildReport:
        """Development path: build the demo from its raw sources (LLM/VLM)."""
        if name != "aldermoor":
            raise LookupError(f"no sources for demo world: {name}")
        if self._builder is None:
            raise RuntimeError("building from sources needs an LLM-backed WorldBuilder")
        return self._builder.build(
            world_id, load_demo_world(include_map=include_map), replace=replace
        )
