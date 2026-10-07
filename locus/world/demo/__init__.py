"""Bundled demo worlds — demos are data (U2 W10, U8 BLM §1, FR-B3, US-1.3, BR-U8-1..5).

The code knows a demo only through ``worlds/manifest.json``. Each entry names a World
File (loaded with no LLM call, BR-U2-28), the region a one-click session starts in, a
credits line and, optionally, source files (notes, structured maps, map images) for
the LLM build path. No demo name, region id or source text lives in code.

Entries are checked once, when ``DemoWorlds`` is built: a bad entry is left out with
a warning and listed in ``problems`` (BR-U8-2). ``check_packaged`` runs the same check
on the installed package (the CI image job, Infra R-04).
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, ValidationError

from locus.shared.models import BuildReport, ConnectionKind, ImportReport
from locus.world.ingestion.service import WorldInputs
from locus.world.worldfile.schema import UnsupportedWorldFile, WorldFile

if TYPE_CHECKING:  # pragma: no cover
    from locus.world.build import WorldBuilder
    from locus.world.worldfile.import_ import WorldFileImporter

logger = logging.getLogger(__name__)

WORLDS_DIR = Path(__file__).resolve().parent / "worlds"  # packaged (pyproject package-data)


class DemoSources(BaseModel):
    """Source files of a demo for the LLM build path, relative to the manifest folder."""

    memos: list[str] = Field(default_factory=list)
    maps: list[str] = Field(default_factory=list)
    map_images: list[str] = Field(default_factory=list)


class DemoInfo(BaseModel):
    """One manifest entry (FD domain-entities §1)."""

    name: str = Field(pattern=r"^[a-z0-9-]{1,40}$")  # also the default world id
    title: str = Field(max_length=60)
    description: str | None = Field(default=None, max_length=300)
    file: str
    start_region_id: str
    credits: str | None = Field(default=None, max_length=200)
    sources: DemoSources | None = None

    @property
    def has_sources(self) -> bool:
        return self.sources is not None and bool(
            self.sources.memos or self.sources.maps or self.sources.map_images
        )


class DemoWorlds:
    """The manifest's demos. ``importer`` is optional: without it the demos can be
    listed and checked but not loaded (``load`` raises RuntimeError)."""

    def __init__(
        self,
        importer: WorldFileImporter | None = None,
        builder: WorldBuilder | None = None,
        *,
        worlds_dir: Path = WORLDS_DIR,
    ) -> None:
        self._importer = importer
        self._builder = builder
        self._dir = worlds_dir
        self._entries, self.problems = _read_manifest(worlds_dir)
        for problem in self.problems:
            logger.warning("demo manifest: %s", problem)

    def list(self) -> list[DemoInfo]:
        return list(self._entries)

    def info(self, name: str) -> DemoInfo:
        for item in self._entries:
            if item.name == name:
                return item
        raise LookupError(f"demo world not found: {name}")

    def load_file(self, name: str) -> WorldFile:
        return _parse(self._dir, self.info(name).file)

    def load(self, name: str, world_id: str, *, replace: bool = True) -> ImportReport:
        """Import the packaged World File into ``world_id`` — LLM-free (BR-U2-28)."""
        if self._importer is None:
            raise RuntimeError("loading a demo needs a World File importer")
        return self._importer.import_(world_id, self.load_file(name), replace=replace)

    def sources(self, name: str, *, include_map: bool = True) -> WorldInputs:
        """The demo's source files as build inputs; LookupError when it has none (BR-U8-4)."""
        info = self.info(name)
        if not info.has_sources:
            raise LookupError(f"no sources for demo world: {name}")
        src = info.sources
        assert src is not None
        images = (
            [
                base64.b64encode(_path(self._dir, p).read_bytes()).decode("ascii")
                for p in src.map_images
            ]
            if include_map
            else []
        )
        return WorldInputs(
            memos=[_path(self._dir, p).read_text(encoding="utf-8") for p in src.memos],
            structured_maps=[json.loads(_path(self._dir, p).read_text("utf-8")) for p in src.maps],
            map_images=images,
            name=info.title,
            description=info.description,
        )

    def build_from_sources(
        self, name: str, world_id: str, *, replace: bool = True, include_map: bool = True
    ) -> BuildReport:
        """Development path: build the demo from its sources (LLM/VLM). The result is not
        the packaged World File: weights come from the build table and the text from the
        LLM (FD BLM §8)."""
        inputs = self.sources(name, include_map=include_map)
        if self._builder is None:
            raise RuntimeError("building from sources needs an LLM-backed WorldBuilder")
        return self._builder.build(world_id, inputs, replace=replace)


def check_packaged() -> list[str]:
    """Problems of the installed package's demos (empty = fine): no entry, an entry that
    fails its check, or a missing source file. Needs no services (CI image job)."""
    demos = DemoWorlds()
    problems = list(demos.problems)
    if not demos.list():
        problems.append("the manifest lists no usable demo world")
    return problems


# --------------------------------------------------------------------------- #
def _read_manifest(worlds_dir: Path) -> tuple[list[DemoInfo], list[str]]:
    try:
        raw = json.loads((worlds_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [], [f"manifest unreadable: {exc}"]
    if not isinstance(raw, list):
        return [], ["manifest must be a list of demo entries"]
    entries: list[DemoInfo] = []
    problems: list[str] = []
    for item in raw:
        try:
            info = DemoInfo.model_validate(item)
        except ValidationError as exc:
            problems.append(f"entry {item!r:.60}: {exc.error_count()} invalid field(s)")
            continue
        problem = _check(worlds_dir, info)
        if problem:
            problems.append(f"{info.name}: {problem}")
        elif any(e.name == info.name for e in entries):
            problems.append(f"{info.name}: listed twice")
        else:
            entries.append(info)
    return entries, problems


def _check(worlds_dir: Path, info: DemoInfo) -> str | None:
    try:
        file = _parse(worlds_dir, info.file)
        for rel in (
            [*info.sources.memos, *info.sources.maps, *info.sources.map_images]
            if info.sources
            else []
        ):
            if not _path(worlds_dir, rel).is_file():
                return f"source file missing: {rel}"
    except (OSError, ValueError, UnsupportedWorldFile) as exc:
        return str(exc)
    if info.start_region_id not in {r.id for r in file.regions}:
        return f"start region {info.start_region_id} is not in {info.file}"
    passable = any(
        info.start_region_id in (c.source_region_id, c.target_region_id)
        and str(c.kind) != ConnectionKind.BLOCKED.value
        and c.weight > 0.0
        for c in file.connections
    )
    if not passable:
        return f"start region {info.start_region_id} has no passable connection"
    return None


def _path(worlds_dir: Path, rel: str) -> Path:
    """A manifest path, refused when it leaves the manifest folder (BR-U8-2)."""
    pure = PurePosixPath(rel)
    if pure.is_absolute() or ".." in pure.parts or not rel:
        raise ValueError(f"path outside the demo folder: {rel!r}")
    return worlds_dir.joinpath(*pure.parts)


def _parse(worlds_dir: Path, rel: str) -> WorldFile:
    return WorldFile.parse(json.loads(_path(worlds_dir, rel).read_text(encoding="utf-8")))
