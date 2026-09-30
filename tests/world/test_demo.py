"""U2 Step 10 — the packaged demo World File loads without any LLM call (EX-26, BR-U2-28/29)
and the source-based demo path survives for development builds."""

from __future__ import annotations

from locus.knowledge.cache import WorldCache
from locus.knowledge.loader import WorldLoader
from locus.world import demo
from locus.world.demo import WORLDS_DIR, DemoWorlds
from locus.world.worldfile import WorldFile, WorldFileExporter, WorldFileImporter
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository


def _demo():
    graph, search = InMemoryGraphRepository(), InMemorySearchRepository()
    cache = WorldCache(WorldLoader(graph))
    importer = WorldFileImporter(graph, search, None, cache, exporter=WorldFileExporter(cache))
    return DemoWorlds(importer), graph, cache


def test_manifest_lists_packaged_files_that_parse() -> None:
    demos, *_ = _demo()
    infos = demos.list()
    assert [d.name for d in infos] == ["aldermoor"]
    for info in infos:
        assert (WORLDS_DIR / info.file).exists()
        file = demos.load_file(info.name)
        assert (
            isinstance(file, WorldFile) and file.format_version == 1 and file.world.id == info.name
        )


def test_demo_loads_without_llm_and_is_idempotent() -> None:  # EX-26
    demos, graph, cache = _demo()
    report = demos.load("aldermoor", "w")
    assert report.ok and report.remapped is True  # file world "aldermoor" -> target "w"
    snap = cache.get("w")
    assert len(snap.topo.regions) == 5
    pairs = {frozenset((c.source_region_id, c.target_region_id)) for c in snap.topo.connections}
    assert len(pairs) == 1 and all(str(c.kind) == "blocked" for c in snap.topo.connections)
    assert len(snap.npcs) >= 5 and all(n.home_region_id in snap.regions_by_id for n in snap.npcs)
    assert any(k.is_global for k in snap.kg.knowledge) and snap.unscoped_knowledge_ids == []
    assert snap.meta is not None and snap.meta.name == "Aldermoor"
    before = len(graph.find_nodes("w", "Region")) + len(graph.find_nodes("w", "NPC"))
    again = demos.load("aldermoor", "w")  # replace, not duplicate (RE A3)
    assert again.replaced is True
    assert len(graph.find_nodes("w", "Region")) + len(graph.find_nodes("w", "NPC")) == before
    # the same file into a second world does not collide (ids remapped per target)
    assert demos.load("aldermoor", "w2").ok and graph.list_world_ids() == ["w", "w2"]


def test_demo_map_image_path_exists() -> None:
    # locus/world/demo/__init__.py -> repository root / examples / demo_world / map.png
    assert demo._MAP_IMAGE.exists(), demo._MAP_IMAGE
    assert demo._MAP_IMAGE.parts[-3:] == ("examples", "demo_world", "map.png")


def test_load_demo_world_sources_include_map_when_present() -> None:
    inputs = demo.load_demo_world(include_map=True)
    assert inputs.memos and inputs.structured_maps and inputs.name == "Aldermoor"
    assert len(inputs.map_images) == 1 and isinstance(inputs.map_images[0], str)  # base64
    assert demo.load_demo_world(include_map=False).map_images == []
