"""world router tests — FastAPI TestClient with fake services in a WorldContainer (U2 12.4)."""

from __future__ import annotations

import io
import json

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from locus.play.turn.guard import TurnGuard
from locus.shared.config import Settings
from locus.shared.models import (
    BuildReport,
    ImportReport,
    Knowledge,
    Provenance,
    Region,
    RegionLevel,
    SourceKind,
    WorldMeta,
)
from locus.shared.storage import graph_mapping as gm
from locus.shared.storage.base import Node
from locus.shared.wiring import SharedContainer
from locus.world.demo import DemoInfo
from locus.world.editor import Editors, WorldCatalog
from locus.world.wiring import WorldContainer
from locus.world.worldfile import WorldFile, WorldFileMeta
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def _file(world_id: str = "w") -> WorldFile:
    region = Region(world_id=world_id, name="Riverton", level=RegionLevel.TOWN, provenance=_prov())
    return WorldFile(format_version=1, world=WorldFileMeta(id=world_id, name="W"), regions=[region])


class _Builder:
    def build(self, world_id, inputs, *, replace=True):
        self.last = (world_id, inputs, replace)
        return BuildReport(world_id=world_id, regions_created=2, knowledge_created=3)


def _editors() -> Editors:
    """The real editor classes over in-memory storage (U3: was an ``_Editor`` fake).

    U8 intended change: U3 review S21 — an edit writes into an existing world, so the
    editors read world ``w`` through the cache, as ``assemble_world`` wires them."""
    from locus.knowledge.cache import WorldCache
    from locus.knowledge.loader import WorldLoader
    from locus.shared.models import WorldMeta
    from locus.shared.storage.persistence import persist_graph

    graph, search = InMemoryGraphRepository(), InMemorySearchRepository()
    persist_graph(graph, search, None, "w", meta=WorldMeta(id="w", name="W"))
    return Editors.assemble(graph, search, cache=WorldCache(WorldLoader(graph)))


class _Exporter:
    def export(self, world_id):
        if world_id == "missing":
            raise LookupError("world not found")
        return _file(world_id)

    def export_world(self, world_id):
        data = self.export(world_id).model_dump(mode="json")
        data["world_id"] = world_id
        return data


class _Importer:
    def __init__(self, *, fail: Exception | None = None) -> None:
        self.calls: list = []
        self.fail = fail

    def import_(self, world_id, file, *, replace=True, force_remap=False):
        self.calls.append((world_id, file, replace, force_remap))
        if self.fail:
            raise self.fail
        return ImportReport(
            world_id=world_id,
            format_version=file.format_version,
            source_world_id=file.world.id,
            remapped=force_remap or file.world.id != world_id,
            forced=force_remap,
            replaced=replace,  # the fake "world" always exists
            counts=file.counts(),
        )


class _Demo:
    def __init__(self) -> None:
        self.loaded: list = []

    def list(self):
        return [
            DemoInfo(
                name="aldermoor",
                title="Aldermoor",
                file="aldermoor.world.json",
                start_region_id="region-riverton",  # U8: a manifest entry names its start
            )
        ]

    def info(self, name):
        for item in self.list():
            if item.name == name:
                return item
        raise LookupError(f"demo world not found: {name}")

    def load(self, name, world_id, *, replace=True):
        self.info(name)
        self.loaded.append((name, world_id, replace))
        return ImportReport(
            world_id=world_id,
            format_version=1,
            source_world_id=name,
            remapped=True,
            replaced=replace,
        )

    def build_from_sources(self, name, world_id, *, replace=True, include_map=True):
        self.map_flag = include_map
        return BuildReport(world_id=world_id, regions_created=5, replaced=replace)


class _GraphRepo:
    def __init__(self, worlds: dict[str, WorldMeta | None] | None = None) -> None:
        self.worlds = worlds if worlds is not None else {"w": None}

    def find_nodes(self, world_id, label, filters=None):
        if label == "Region" and world_id in self.worlds:
            return [Node(id="r1", label="Region", world_id=world_id, properties={})]
        if label == "WorldMeta" and self.worlds.get(world_id) is not None:
            return [gm.worldmeta_to_node(self.worlds[world_id])]
        return []

    def list_world_ids(self):
        return sorted(self.worlds)


class _Session:
    def __init__(self, sid: str, status: str) -> None:
        self.id, self.status = sid, status


class _Sessions:
    def __init__(self, sessions: list[_Session]) -> None:
        self._sessions = sessions
        self.closed: list[str] = []

    def list_sessions(self, world_id):
        return self._sessions

    def close_session(self, sid):
        self.closed.append(sid)


class _Play:
    def __init__(self, sessions: list[_Session]) -> None:
        self.sessions = _Sessions(sessions)
        self.guard = TurnGuard()  # U4: the replace gate pre-flights running turns


def _client(
    *, editors=None, builder="default", importer=None, demo=None, graph=None, play=None, loc=None
):
    graph = graph or _GraphRepo()
    world = WorldContainer(
        cache=None,
        editors=editors or _editors(),
        catalog=WorldCatalog(graph),
        exporter=_Exporter(),
        importer=importer or _Importer(),
        demo=demo or _Demo(),
        builder=_Builder() if builder == "default" else builder,
        augmentation=None,
        wiki_admin=None,
        cross_world=None,
    )
    shared = SharedContainer(settings=Settings(), graph=graph)
    return TestClient(create_app(world=world, shared=shared, play=play, localization=loc))


# --- build ------------------------------------------------------------------- #
def test_build_world_endpoint() -> None:
    body = {"memos": ["a note"], "structured_maps": [], "map_images": [], "concept_arts": []}
    r = _client().post("/api/world/worlds/w/build", json=body)
    assert r.status_code == 200 and r.json()["regions_created"] == 2
    assert r.json()["ok"] is True and r.json()["closed_session_ids"] == []


def test_build_upload_multipart_builds_inputs() -> None:
    builder = _Builder()
    files = [
        ("memos", ("a.txt", io.BytesIO(b"a note"), "text/plain")),
        ("maps", ("m.json", io.BytesIO(b'{"regions": []}'), "application/json")),
        ("images", ("map.png", io.BytesIO(b"\x89PNG"), "image/png")),
    ]
    r = _client(builder=builder).post(
        "/api/world/worlds/w/build/upload", files=files, data={"name": "My World"}
    )
    assert r.status_code == 200
    _wid, inputs, replace = builder.last
    assert inputs.memos == ["a note"] and inputs.structured_maps == [{"regions": []}]
    assert inputs.map_images == ["iVBORw=="] and inputs.name == "My World" and replace is True
    bad = [("maps", ("m.json", io.BytesIO(b"not json"), "application/json"))]
    assert _client().post("/api/world/worlds/w/build/upload", files=bad).status_code == 422


def test_llm_free_container_serves_files_and_demo_but_not_build() -> None:  # R-14
    client = _client(builder=None)
    assert client.post("/api/world/worlds/w/build", json={"memos": ["x"]}).status_code == 503
    assert client.post("/api/world/worlds/w/augmentation/runs").status_code == 503
    assert client.get("/api/world/worlds/w/related-priors").status_code == 503
    assert client.get("/api/world/worlds/w/file").status_code == 200
    assert client.get("/api/world/demos").status_code == 200
    assert client.post("/api/world/worlds/w/demo/aldermoor").status_code == 200
    assert client.get("/api/world/worlds").status_code == 200
    assert client.post("/api/world/worlds/w/demo/aldermoor/build").status_code == 503


# --- World File -------------------------------------------------------------- #
def test_world_file_download_and_import_roundtrip() -> None:
    importer = _Importer()
    client = _client(importer=importer)
    r = client.get("/api/world/worlds/w/file")
    assert r.status_code == 200
    assert 'filename="w.world.json"' in r.headers["content-disposition"]
    raw = json.loads(r.content)
    assert raw["format_version"] == 1 and raw["world"]["id"] == "w" and "world_id" not in raw
    r2 = client.post("/api/world/worlds/w2/file", json=raw)
    assert r2.status_code == 200 and r2.json()["remapped"] is True
    wid, file, replace, forced = importer.calls[-1]
    assert wid == "w2" and isinstance(file, WorldFile) and file.world.id == "w" and not forced
    assert client.get("/api/world/worlds/missing/file").status_code == 404
    export = client.get("/api/world/worlds/w/export").json()
    assert export["world_id"] == "w" and export["format_version"] == 1  # compat keys kept


def test_world_file_import_rejects_unsupported_with_422() -> None:  # EX-1 via API
    client = _client()
    r = client.post(
        "/api/world/worlds/w/file", json={"format_version": 2, "world": {"id": "w", "name": "W"}}
    )
    assert r.status_code == 422 and "format_version" in r.json()["detail"]
    assert client.post("/api/world/worlds/w/file", json={"regions": []}).status_code == 422
    assert client.post("/api/world/worlds/w/file", json={"format_version": 1}).status_code == 422


def test_world_file_import_remap_flag_and_upload() -> None:  # EX-3 via API
    importer = _Importer()
    client = _client(importer=importer)
    raw = _file("w").model_dump(mode="json")
    r = client.post("/api/world/worlds/w/file?remap=true", json=raw)
    assert r.status_code == 200 and r.json()["forced"] is True
    assert importer.calls[-1][3] is True
    files = {"file": ("w.world.json", io.BytesIO(json.dumps(raw).encode()), "application/json")}
    r = client.post("/api/world/worlds/w/file/upload", files=files, data={"replace": "false"})
    assert r.status_code == 200 and importer.calls[-1][2] is False
    bad = {"file": ("x.json", io.BytesIO(b"nope"), "application/json")}
    assert client.post("/api/world/worlds/w/file/upload", files=bad).status_code == 422


# --- replace confirmation (NFR-9 / BR-U2-25, EX-24) --------------------------- #
def test_replace_with_open_sessions_needs_confirm_and_closes_only_open() -> None:
    play = _Play([_Session("s-open", "open"), _Session("s-closed", "closed")])
    importer = _Importer()
    client = _client(importer=importer, play=play)
    raw = _file("w").model_dump(mode="json")
    r = client.post("/api/world/worlds/w/file", json=raw)
    assert r.status_code == 409 and r.json()["detail"]["open_sessions"] == 1
    assert importer.calls == [] and play.sessions.closed == []
    r = client.post("/api/world/worlds/w/file?confirm=true", json=raw)
    assert r.status_code == 200 and r.json()["closed_session_ids"] == ["s-open"]
    assert play.sessions.closed == ["s-open"]
    # replace=false never asks
    play2 = _Play([_Session("s-open", "open")])
    r = _client(play=play2).post("/api/world/worlds/w/file?replace=false", json=raw)
    assert r.status_code == 200 and play2.sessions.closed == []
    # a failing import never closes the sessions (review #6)
    play3 = _Play([_Session("s-open", "open")])
    failing = _client(importer=_Importer(fail=RuntimeError("boom")), play=play3)
    with pytest.raises(RuntimeError):
        failing.post("/api/world/worlds/w/file?confirm=true", json=raw)
    assert play3.sessions.closed == []
    # a session mid-turn blocks the replace outright, even with confirm (U4-2 #3):
    # closing it would fail *after* the world was destroyed
    play5 = _Play([_Session("s-open", "open")])
    play5.guard.acquire("s-open", "run-1")
    busy_client = _client(importer=_Importer(), play=play5)
    rbusy = busy_client.post("/api/world/worlds/w/file?confirm=true", json=raw)
    assert rbusy.status_code == 409 and rbusy.json()["detail"]["busy_sessions"] == 1
    assert play5.sessions.closed == []
    play5.guard.release("s-open")
    assert busy_client.post("/api/world/worlds/w/file?confirm=true", json=raw).status_code == 200
    # a misspelled demo name is a 404 before the gate, sessions untouched
    play4 = _Play([_Session("s-open", "open")])
    r404 = _client(play=play4).post("/api/world/worlds/w/demo/nope?confirm=true")
    assert r404.status_code == 404 and play4.sessions.closed == []
    # demo load and build go through the same gate
    assert (
        _client(play=_Play([_Session("s", "open")]))
        .post("/api/world/worlds/w/demo/aldermoor")
        .status_code
        == 409
    )
    assert (
        _client(play=_Play([_Session("s", "open")]))
        .post("/api/world/worlds/w/build", json={"memos": ["x"]})
        .status_code
        == 409
    )


def test_replace_without_play_boundary_proceeds() -> None:
    r = _client().post("/api/world/worlds/w/file", json=_file("w").model_dump(mode="json"))
    assert r.status_code == 200 and r.json()["closed_session_ids"] == []


# --- world list / demos ------------------------------------------------------ #
def test_list_worlds_reports_meta_and_open_sessions() -> None:
    graph = _GraphRepo({"a": WorldMeta(id="a", name="Alpha", last_writer="import"), "old": None})
    play = _Play([_Session("s1", "open"), _Session("s2", "closed")])
    rows = {
        row["id"]: row for row in _client(graph=graph, play=play).get("/api/world/worlds").json()
    }
    assert rows["a"]["name"] == "Alpha" and rows["a"]["last_writer"] == "import"
    assert rows["a"]["region_count"] == 1 and rows["a"]["open_sessions"] == 1
    assert rows["old"]["name"] == "old" and rows["old"]["updated_at"] is None
    assert _client(graph=graph).get("/api/world/worlds").json()[0]["open_sessions"] is None


def test_demo_list_and_load() -> None:
    demo = _Demo()
    client = _client(demo=demo)
    listed = client.get("/api/world/demos").json()[0]
    # U8 intended change: the card fields only — no file or source paths (domain-entities §1)
    assert listed == {
        "name": "aldermoor",
        "title": "Aldermoor",
        "description": None,
        "credits": None,
        "start_region_id": "region-riverton",
        "has_sources": False,
    }
    r = client.post("/api/world/worlds/w/demo/aldermoor")
    assert r.status_code == 200 and demo.loaded == [("aldermoor", "w", True)]
    assert client.post("/api/world/worlds/w/demo/nope").status_code == 404
    assert client.post("/api/world/worlds/w/demo/aldermoor/build").json()["regions_created"] == 5


# --- graph / edits (unchanged behaviour) -------------------------------------- #
def test_graph_summary_endpoint() -> None:
    r = _client().get("/api/world/worlds/w/graph")
    assert (
        r.status_code == 200 and r.json()["region_count"] == 1 and r.json()["region_ids"] == ["r1"]
    )


def test_upsert_region_endpoint() -> None:
    region = Region(world_id="w", name="Town", level=RegionLevel.TOWN, provenance=_prov())
    r = _client().put(f"/api/world/worlds/w/regions/{region.id}", json=region.model_dump())
    assert r.status_code == 200 and r.json()["name"] == "Town"


def test_delete_node_endpoint() -> None:
    # U3 intended change: 이탈 2 — the generic node delete is gone; deletes go by kind
    r = _client().delete("/api/world/worlds/w/nodes/n9")
    assert r.status_code in (404, 405)


def test_upsert_knowledge_endpoint() -> None:
    k = Knowledge(world_id="w", statement="fact", title="fact", provenance=_prov())
    r = _client().put(f"/api/world/worlds/w/knowledge/{k.id}", json=k.model_dump())
    assert r.status_code == 200 and r.json()["statement"] == "fact"


def test_world_file_download_supports_non_ascii_ids() -> None:  # review #13
    r = _client().get("/api/world/worlds/%EB%8D%B0%EB%AA%A8/file")
    assert r.status_code == 200
    cd = r.headers["content-disposition"]
    assert "filename*=UTF-8''%EB%8D%B0%EB%AA%A8.world.json" in cd and 'filename="' in cd


def test_demo_build_from_sources_with_map_flag() -> None:
    demo = _Demo()
    r = _client(demo=demo).post("/api/world/worlds/w/demo/aldermoor/build?with_map=false")
    assert r.status_code == 200 and demo.map_flag is False


def test_u5_a_replace_with_no_open_session_still_purges_the_worlds_translations() -> None:
    """FD review R-13: the purge must not sit behind the session step's early return."""
    from locus.localization import TranslationService
    from locus.localization.models import Translation
    from locus.localization.storage.memory_repo import InMemoryTranslationRepository
    from locus.localization.translator import Translator
    from locus.localization.wiring import LocalizationContainer

    class _NoLLM:
        def complete(self, prompt, *, system=None):  # pragma: no cover
            return ""

        def structured(self, prompt, schema, *, system=None):  # pragma: no cover
            raise NotImplementedError

    store = InMemoryTranslationRepository()
    loc = LocalizationContainer(translations=TranslationService(store, Translator(_NoLLM())))

    def row(sid: str, world: str) -> Translation:
        return Translation(
            source_kind="knowledge",
            source_id=sid,
            source_field="statement",
            text="번역",
            source_hash="h",
            world_id=world,
        )

    store.upsert_many([row("k1", "w"), row("k2", "other")])
    client = _client(play=_Play([]), loc=loc)  # no open sessions at all
    raw = _file("w").model_dump(mode="json")
    assert client.post("/api/world/worlds/w/file?confirm=true", json=raw).status_code == 200
    assert store.get_many([("knowledge", "k1", "statement")], "ko") == {}  # purged
    assert store.get_many([("knowledge", "k2", "statement")], "ko")  # other world kept
    # the demo route shares the helper
    store.upsert_many([row("k3", "w")])
    assert client.post("/api/world/worlds/w/demo/aldermoor?confirm=true").status_code == 200
    assert store.get_many([("knowledge", "k3", "statement")], "ko") == {}
