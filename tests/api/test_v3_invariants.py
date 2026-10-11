"""V3 invariants (FR-L4, BR-V3-26·27, TP-V3-12, code plan R-08a): seeding writes only the
translation cache, never the graph or the search index; the World File stays English;
the shared i18n module stays at the bottom of the boundaries."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from api.main import create_app
from api.schemas import seed_demo_translations
from locus.knowledge.wiring import assemble_knowledge
from locus.localization import InMemoryTranslationRepository, assemble_localization
from locus.play import InMemoryPlayRepository
from locus.play.turn.executor import SyncTurnExecutor
from locus.play.wiring import assemble_play
from locus.shared.config import Settings
from locus.shared.wiring import SharedContainer
from locus.world.wiring import assemble_world
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository

HANGUL = re.compile(r"[가-힣]")
WRITES_GRAPH = (
    "upsert_nodes",
    "upsert_edges",
    "replace_edges",
    "replace_nodes",
    "delete_edges",
    "delete_node",
    "delete_world",
)
WRITES_SEARCH = ("index", "delete", "delete_world")


def _counting(cls, names):
    class Counting(cls):
        writes = 0

    for n in names:

        def wrap(self, *a, _n=n, **k):
            type(self).writes += 1
            return getattr(cls, _n)(self, *a, **k)

        setattr(Counting, n, wrap)
    return Counting


def _app():
    graph = _counting(InMemoryGraphRepository, WRITES_GRAPH)()
    search = _counting(InMemorySearchRepository, WRITES_SEARCH)()
    shared = SharedContainer(settings=Settings(), graph=graph, search=search, llm=None)
    knowledge = assemble_knowledge(shared)
    world = assemble_world(shared, knowledge)
    play = assemble_play(
        shared, knowledge, repo=InMemoryPlayRepository(), executor=SyncTurnExecutor()
    )
    loc = assemble_localization(shared, store=InMemoryTranslationRepository())
    app = create_app(shared=shared, world=world, play=play, localization=loc)
    return TestClient(app), world, loc, graph, search


def test_seeding_writes_no_graph_and_no_index() -> None:  # TP-V3-12 (R-08a: the seeding step only)
    client, world, loc, graph, search = _app()
    demo = client.get("/api/world/demos").json()[0]["name"]
    assert client.post(f"/api/world/worlds/{demo}/demo/{demo}").status_code == 200
    graph_before, search_before = type(graph).writes, type(search).writes
    assert graph_before > 0 and search_before > 0  # the import itself writes; those are not counted
    report = SimpleNamespace(ok=True, remapped=False)
    got = seed_demo_translations(
        loc, world.demo, demo, world_id=demo, report=report, langs=["ko", "en"]
    )
    assert got.seeded == 123
    assert (type(graph).writes, type(search).writes) == (graph_before, search_before)


def test_the_world_file_and_the_export_stay_english() -> None:  # FR-L4
    client, _world, _loc, _g, _s = _app()
    demo = client.get("/api/world/demos").json()[0]["name"]
    assert client.post(f"/api/world/worlds/{demo}/demo/{demo}").json()["translations_seeded"] == 123
    for path in (f"/api/world/worlds/{demo}/file", f"/api/world/worlds/{demo}/export"):
        r = client.get(path)
        assert r.status_code == 200 and not HANGUL.search(r.text), path


def test_the_shared_i18n_module_imports_nothing_above_shared() -> None:  # BR-V3-26
    source = Path(__file__).resolve().parents[2] / "locus" / "shared" / "models" / "i18n.py"
    imported = set()
    for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
    locus = {m for m in imported if m.startswith("locus")}
    assert locus and all(m.startswith("locus.shared") for m in locus), locus
