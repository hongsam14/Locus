"""Bundled demo worlds — demos are data (U2 W10, U8 BLM §1, FR-B3, US-1.3, BR-U8-1..5).

The code knows a demo only through ``worlds/manifest.json``. Each entry names a World
File (loaded with no LLM call, BR-U2-28), the region a one-click session starts in, a
credits line and, optionally, source files (notes, structured maps, map images) for
the LLM build path. No demo name, region id or source text lives in code.

Entries are checked once, when ``DemoWorlds`` is built: a bad entry is left out with
a warning and listed in ``problems`` (BR-U8-2). ``check_packaged`` runs the same check
on the installed package (the CI image job, Infra R-04).

V3 (FR-L3, FR-C11): an entry may carry card text per language (``i18n``) and a
translation file per language (``translations``). The World File's ``world.id`` must be
the entry's ``name`` — [play now] loads a demo into its own name, and another id would
be remapped away from ``start_region_id``. A translation file's problems are listed in
``problems`` too, so the CI check fails, but they never leave the demo out: at run
time the readable entries are seeded and the rest of the demo shows in English (Q3=A).
A malformed ``i18n``/``translations`` key or card text is a manifest error like a bad
English ``title`` and does leave the entry out (code plan memo R-06).
"""

from __future__ import annotations

import base64
import builtins
import json
import logging
import re
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, ValidationError, field_validator

from locus.shared.models import BuildReport, ConnectionKind, ImportReport
from locus.shared.models.i18n import SOURCE_LANG, TranslationEntry, TranslationFile, source_hash
from locus.world.ingestion.service import WorldInputs
from locus.world.worldfile.remap import file_ids, remap_ids, remapped_id, set_world_id
from locus.world.worldfile.schema import UnsupportedWorldFile, WorldFile
from locus.world.worldfile.texts import TextKey, translatable_texts

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


class DemoCardText(BaseModel):
    """A demo card's text in one language (V3, Q4=A); the same caps as the English."""

    title: str = Field(max_length=60)
    description: str | None = Field(default=None, max_length=300)
    credits: str | None = Field(default=None, max_length=200)


_LANG_KEY = re.compile(r"^[a-z]{2}$")


class DemoInfo(BaseModel):
    """One manifest entry (FD domain-entities §1; V3 adds ``i18n`` and ``translations``)."""

    name: str = Field(pattern=r"^[a-z0-9-]{1,40}$")  # also the default world id
    title: str = Field(max_length=60)
    description: str | None = Field(default=None, max_length=300)
    file: str
    start_region_id: str
    credits: str | None = Field(default=None, max_length=200)
    sources: DemoSources | None = None
    i18n: dict[str, DemoCardText] = Field(default_factory=dict)  # lang -> card text (V3)
    translations: dict[str, str] = Field(default_factory=dict)  # lang -> file, manifest-relative

    @field_validator("i18n", "translations")
    @classmethod
    def _lang_keys(cls, value: dict) -> dict:
        for lang in value:
            if not _LANG_KEY.fullmatch(lang) or lang == SOURCE_LANG:
                raise ValueError(f"not a display language key: {lang!r}")
        return value

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

    def card(self, name: str, lang: str) -> DemoCardText | None:
        """The demo card's text in ``lang`` from the manifest, or ``None`` (V3)."""
        return self.info(name).i18n.get(lang)

    def translation_langs(self, name: str) -> builtins.list[str]:
        return sorted(self.info(name).translations)

    def translations(
        self, name: str, lang: str, *, target_world_id: str, remapped: bool
    ) -> builtins.list[TranslationEntry]:
        """The readable entries of the demo's ``lang`` file with their ids moved the way
        the import moved the World File (BR-V3-18/19): when ``remapped``, an id of the file
        becomes ``remapped_id(target, id)``; a ``world`` entry for the file's world always
        becomes ``target_world_id``. Other ids stay and are dropped as unknown when seeded.
        An unreadable file gives ``[]`` and a warning (Q3=A)."""
        rel = self.info(name).translations.get(lang)
        if rel is None:
            return []
        try:
            entries = _read_translations(self._dir, rel).entries
        except (OSError, ValueError) as exc:
            logger.warning("demo %s translations %s unreadable: %s", name, lang, exc)
            return []
        file = self.load_file(name)
        known = file_ids(file)
        out: builtins.list[TranslationEntry] = []
        for entry in entries:
            new_id = entry.id
            if entry.kind == "world":
                if entry.id == file.world.id:
                    new_id = target_world_id
            elif remapped and entry.id in known:
                new_id = remapped_id(target_world_id, entry.id)
            out.append(entry if new_id == entry.id else entry.model_copy(update={"id": new_id}))
        return out

    def texts(self, name: str, *, target_world_id: str, remapped: bool) -> dict[TextKey, str]:
        """The demo's English texts under the ids the import gave them (BR-V3-20)."""
        file = self.load_file(name)
        moved = (
            remap_ids(file, target_world_id) if remapped else set_world_id(file, target_world_id)
        )
        return translatable_texts(moved)

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
            entries.append(info)  # translation problems are listed but keep the entry
            problems.extend(f"{info.name}: {p}" for p in _check_translations(worlds_dir, info))
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
    if file.world.id != info.name:  # FR-C11: [play now] would start in a remapped world
        return f"{info.file} is world {file.world.id!r}, not {info.name!r}; the names must match"
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


_SHOW = 3  # problems of one kind named in a line (BR-V3-09)


def _check_translations(worlds_dir: Path, info: DemoInfo) -> list[str]:
    """What is wrong with the entry's translation files (BR-V3-08 (a)-(h)); [] when fine.
    Runs after ``_check``, so the World File is readable."""
    if not info.translations:
        return []
    file = _parse(worlds_dir, info.file)
    texts = translatable_texts(file)
    out: list[str] = []
    for lang, rel in sorted(info.translations.items()):
        head = f"translations {lang}"
        try:
            tr = _read_translations(worlds_dir, rel)
        except (OSError, ValueError) as exc:
            out.append(f"{head}: {exc}")
            continue
        if tr.lang != lang:
            out.append(f"{head}: the file says lang {tr.lang!r}")
        if tr.world_id != file.world.id:
            out.append(f"{head}: made for world {tr.world_id!r}, not {file.world.id!r}")
        seen: dict[TextKey, int] = {}
        for entry in tr.entries:
            seen[entry.key] = seen.get(entry.key, 0) + 1
        twice = [k for k, n in seen.items() if n > 1]
        if twice:
            out.append(f"{head}: duplicate {_keys(twice)}")
        unknown = [k for k in seen if k not in texts]
        if unknown:
            out.append(f"{head}: unknown {_keys(unknown)}")
        stale = [
            e for e in tr.entries if e.key in texts and e.source_hash != source_hash(texts[e.key])
        ]
        if stale:
            shown = "; ".join(
                f"{_key(e.key)}: file {_clip(e.source)!r} ≠ world {_clip(texts[e.key])!r}"
                for e in stale[:_SHOW]
            )
            out.append(f"{head}: stale {shown}{_more(len(stale))}")
        missing = [k for k in texts if k not in seen]
        if missing:
            out.append(
                f"{head}: {len(missing)} texts untranslated: "
                f"{', '.join(_key(k) for k in missing[:5])}{_more(len(missing), 5)}"
            )
    return out


def _key(key: TextKey) -> str:
    kind, id_, field = key
    return f"{kind} {id_}.{field}"


def _keys(keys: list[TextKey]) -> str:
    return ", ".join(_key(k) for k in keys[:_SHOW]) + _more(len(keys))


def _more(n: int, shown: int = _SHOW) -> str:
    return f" and {n - shown} more" if n > shown else ""


def _clip(text: str, limit: int = 60) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _read_translations(worlds_dir: Path, rel: str) -> TranslationFile:
    path = _path(worlds_dir, rel)  # ValueError outside the folder (BR-V3-06)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"unreadable {rel}: {exc}") from exc
    return TranslationFile.parse(data)


def _path(worlds_dir: Path, rel: str) -> Path:
    """A manifest path, refused when it leaves the manifest folder (BR-U8-2)."""
    pure = PurePosixPath(rel)
    if pure.is_absolute() or ".." in pure.parts or not rel:
        raise ValueError(f"path outside the demo folder: {rel!r}")
    return worlds_dir.joinpath(*pure.parts)


def _parse(worlds_dir: Path, rel: str) -> WorldFile:
    return WorldFile.parse(json.loads(_path(worlds_dir, rel).read_text(encoding="utf-8")))
