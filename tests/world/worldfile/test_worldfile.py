"""U2 Step 9 — World File round trip (TP-U2-1), remap (TP-U2-2), legacy v0 (TP-U2-6),
parse rules (EX-1/2), forced remap (EX-3), id collision (EX-4), broken refs (EX-5/13),
meta touch (EX-23)."""

from __future__ import annotations

import random

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from locus.knowledge.cache import WorldCache
from locus.knowledge.loader import WorldLoader
from locus.shared.models import NPC, Provenance, ScopeLink, ScopeType, SourceKind
from locus.world.build import WorldExistsError
from locus.world.worldfile import (
    UnsupportedWorldFile,
    WorldFile,
    WorldFileExporter,
    WorldFileImporter,
    WorldFileMeta,
    file_ids,
    remap_ids,
    sort_sections,
    validate_references,
)
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository
from tests.world.strategies import world_files


def _demo_file(world_id: str) -> WorldFile:
    """The packaged Aldermoor World File re-stamped to ``world_id`` — a rich, deterministic
    fixture (no ``.example()`` flakiness)."""
    import json

    from locus.world.demo import WORLDS_DIR
    from locus.world.worldfile import set_world_id

    raw = json.loads((WORLDS_DIR / "aldermoor.world.json").read_text(encoding="utf-8"))
    return set_world_id(WorldFile.parse(raw), world_id)


def _dump(file: WorldFile) -> dict:
    return sort_sections(file).model_dump(mode="json", exclude={"exported_at"})


def _stack(seed: int | None = None):
    graph = InMemoryGraphRepository(shuffle=random.Random(seed) if seed is not None else None)
    search = InMemorySearchRepository()
    cache = WorldCache(WorldLoader(graph))
    exporter = WorldFileExporter(cache)
    importer = WorldFileImporter(graph, search, None, cache, exporter=exporter)
    return graph, search, cache, exporter, importer


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(world_files(), st.integers(min_value=0, max_value=1_000))
def test_export_import_export_is_stable(file: WorldFile, seed: int) -> None:  # TP-U2-1
    _g, _s, _c, exporter, importer = _stack(seed)
    report = importer.import_("src", file)
    assert report.ok and report.remapped is False and report.replaced is False
    out = exporter.export("src")
    assert _dump(out) == _dump(file)  # storage order scrambled, file identical
    stamp = {"exported_at": None}
    assert (
        exporter.export("src").model_copy(update=stamp).to_json()
        == out.model_copy(update=stamp).to_json()
    )  # byte-identical text apart from the timestamp
    again = importer.import_("src", out, replace=True)
    assert again.ok and again.replaced is True
    assert _dump(exporter.export("src")) == _dump(file)


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(world_files())
def test_remap_is_deterministic_and_stable_at_import_level(file: WorldFile) -> None:  # TP-U2-2
    once, twice = remap_ids(file, "dst"), remap_ids(file, "dst")
    assert _dump(once) == _dump(twice) and once.world.id == "dst"
    assert file_ids(once).isdisjoint(file_ids(file)) or not file_ids(file)
    assert all(item.world_id == "dst" for item in once.regions + once.npcs + once.knowledge)
    _f, warnings = validate_references(once)
    assert warnings == []  # every in-file reference still resolves
    external = {
        r
        for item in file.regions + file.knowledge + file.connections
        for r in item.provenance.refs
        if r == "chg-external"
    }
    kept = {
        r
        for item in once.regions + once.knowledge + once.connections
        for r in item.provenance.refs
        if r == "chg-external"
    }
    assert external == kept  # external refs untouched (FD R-13)
    _g, _s, _c, exporter, importer = _stack()
    assert importer.import_("dst", once).remapped is False  # already the target's file
    assert _dump(exporter.export("dst")) == _dump(once)


@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(world_files(world_id="A"))
def test_legacy_export_is_read_and_remapped_across_worlds(file: WorldFile) -> None:  # TP-U2-6
    legacy = {
        "world_id": "A",
        "regions": [r.model_dump(mode="json") for r in file.regions],
        "connections": [c.model_dump(mode="json") for c in file.connections],
        "entities": [e.model_dump(mode="json") for e in file.entities],
        "knowledge": [k.model_dump(mode="json") for k in file.knowledge],
        "scopes": [s.model_dump(mode="json") for s in file.scopes],
    }
    parsed = WorldFile.parse(legacy)
    assert parsed.format_version == 0 and parsed.world.id == "A" and parsed.npcs == []
    _g, _s, _c, exporter, importer = _stack()
    into_b = importer.import_("B", parsed)
    assert into_b.remapped is True and into_b.ok
    assert file_ids(exporter.export("B")).isdisjoint(file_ids(file)) or not file_ids(file)
    into_a = importer.import_("A", parsed)
    assert into_a.remapped is False and into_a.ok
    out = exporter.export("A")
    assert out.format_version == 1
    for name in ("regions", "connections", "entities", "knowledge", "scopes"):
        assert len(getattr(out, name)) == len(getattr(file, name))


def test_parse_rejects_unsupported_and_non_world_files() -> None:  # EX-1
    with pytest.raises(UnsupportedWorldFile, match="format_version"):
        WorldFile.parse({"format_version": 2, "world": {"id": "w", "name": "w"}})
    with pytest.raises(UnsupportedWorldFile, match="world_id"):
        WorldFile.parse({"regions": []})
    with pytest.raises(UnsupportedWorldFile):
        WorldFile.parse([])  # type: ignore[arg-type]


def test_parse_ignores_unknown_keys_but_rejects_missing_required() -> None:  # EX-2
    raw = {
        "format_version": 1,
        "world": {"id": "w", "name": "W", "future": 1},
        "future_section": [1],
        "regions": [
            {
                "id": "r1",
                "world_id": "w",
                "name": "R",
                "level": "town",
                "novel": True,
                "provenance": {"source": "input", "novel": "x"},
            }
        ],
    }
    file = WorldFile.parse(raw)
    assert [r.id for r in file.regions] == ["r1"]
    with pytest.raises(UnsupportedWorldFile, match="invalid world file"):
        WorldFile.parse(
            {
                "format_version": 1,
                "world": {"id": "w", "name": "W"},
                "regions": [{"id": "r1", "world_id": "w", "level": "town"}],
            }
        )  # no name


def test_forced_remap_changes_every_id_even_for_the_same_world() -> None:  # EX-3 (FD R-12)
    file = _demo_file("w")
    _g, _s, _c, exporter, importer = _stack()
    report = importer.import_("w", file, force_remap=True)
    assert report.remapped is True and report.forced is True
    assert file_ids(exporter.export("w")).isdisjoint(file_ids(file)) or not file_ids(file)


def test_id_collision_with_another_world_is_reported_and_recoverable() -> None:  # EX-4
    file = _demo_file("a")
    graph, _s, _c, _e, importer = _stack()
    assert importer.import_("a", file).ok
    clash = file.model_copy(update={"world": WorldFileMeta(id="b", name="B")})  # same ids, "b"
    report = importer.import_("b", clash)
    if file_ids(file):
        assert report.ok is False and "remap=true" in report.errors[0].message
    assert importer.import_("b", clash, force_remap=True).ok  # the documented recovery


def test_broken_references_are_dropped_with_errors() -> None:  # EX-5 / EX-13
    file = _demo_file("w")
    prov = Provenance(source=SourceKind.INPUT)
    ghost_scope = ScopeLink(
        world_id="w", knowledge_id="k-ghost", region_id="r-ghost", scope_type=ScopeType.DIRECT
    )
    ghost_npc = NPC(
        world_id="w",
        name="Nobody",
        role="x",
        description="d",
        home_region_id="r-ghost",
        provenance=prov,
    )
    broken = file.model_copy(
        update={"scopes": file.scopes + [ghost_scope], "npcs": file.npcs + [ghost_npc]}
    )
    _g, _s, _c, exporter, importer = _stack()
    report = importer.import_("w", broken)
    assert report.ok is False and len(report.errors) == 2
    out = exporter.export("w")
    assert len(out.npcs) == len(file.npcs) and len(out.scopes) == len(file.scopes)


def test_import_stamps_world_meta_and_backs_up_on_replace(tmp_path) -> None:  # EX-23
    file = _demo_file("w")
    graph, search, cache, exporter, _ = _stack()
    importer = WorldFileImporter(graph, search, None, cache, exporter=exporter, backup_dir=tmp_path)
    first = importer.import_("w", file)
    meta = cache.get("w").meta
    assert meta is not None and meta.last_writer == "import" and meta.name == file.world.name
    with pytest.raises(WorldExistsError):
        importer.import_("w", file, replace=False)
    second = importer.import_("w", file, replace=True)
    assert (
        second.replaced
        and second.backup_path
        and (tmp_path / second.backup_path.split("/")[-1]).exists()
    )
    assert cache.get("w").meta.updated_at >= meta.updated_at and first.ok


def test_validate_references_clears_optional_dangling_refs() -> None:  # review tail
    from locus.shared.models import ConnectionEdge, ConnectionKind, Entity, EntityType, Knowledge

    prov = Provenance(source=SourceKind.INPUT)
    file = _demo_file("w")
    region = file.regions[0]
    ghost_entity = Entity(
        world_id="w",
        name="Ghost",
        entity_type=EntityType.PLACE,
        located_in="r-ghost",
        provenance=prov,
    )
    ghost_conn = ConnectionEdge(
        world_id="w",
        source_region_id=region.id,
        target_region_id=file.regions[1].id,
        kind=ConnectionKind.RIVER,
        wiki_prior_ref="p-ghost",
        provenance=prov,
    )
    ghost_k = Knowledge(
        world_id="w", statement="s", title="t", about_entity_ids=["e-ghost"], provenance=prov
    )
    broken = file.model_copy(
        update={
            "entities": file.entities + [ghost_entity],
            "connections": file.connections + [ghost_conn],
            "knowledge": file.knowledge + [ghost_k],
        }
    )
    fixed, warnings = validate_references(broken)
    assert all(w.severity == "warning" for w in warnings) and len(warnings) == 3
    assert next(e for e in fixed.entities if e.id == ghost_entity.id).located_in is None
    assert next(c for c in fixed.connections if str(c.kind) == "river").wiki_prior_ref is None
    assert next(k for k in fixed.knowledge if k.id == ghost_k.id).about_entity_ids == []


def test_parse_rejects_non_list_sections_and_strips_position_keys() -> None:
    with pytest.raises(UnsupportedWorldFile, match="must be a list"):
        WorldFile.parse({"format_version": 1, "world": {"id": "w", "name": "W"}, "regions": 5})
    raw = {
        "format_version": 1,
        "world": {"id": "w", "name": "W"},
        "regions": [
            {
                "id": "r1",
                "world_id": "w",
                "name": "R",
                "level": "town",
                "position": {"x": 0.1, "y": 0.2, "z": 9},
                "provenance": {"source": "input"},
            }
        ],
    }
    assert WorldFile.parse(raw).regions[0].position is not None
