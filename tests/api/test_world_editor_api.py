"""U3 editor API (BLM §7 〔Step 1.3 정정〕, BR-U3-5/6/16, NFR-3 ④⑤, NFR-4)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from locus.knowledge.cache import WorldCache
from locus.knowledge.loader import WorldLoader
from locus.knowledge.wiring import KnowledgeContainer
from locus.play.models import Player
from locus.shared.config import Settings
from locus.shared.models import (
    NPC,
    ConnectionEdge,
    ConnectionKind,
    Knowledge,
    PriorType,
    Provenance,
    Region,
    RegionLevel,
    ScopeLink,
    SourceKind,
    WikiPrior,
    WorldMeta,
)
from locus.shared.storage.persistence import persist_graph
from locus.shared.wiring import SharedContainer
from locus.world.editor import Editors, WorldCatalog
from locus.world.npc_drafts import NpcDraftService
from locus.world.wiki import WikiAdmin
from locus.world.wiring import WorldContainer, assemble_world
from tests.api.play_fixtures import play_container
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


class _CountingGraph(InMemoryGraphRepository):
    def __init__(self) -> None:
        super().__init__()
        self.reads: list[tuple[str, str]] = []

    def find_nodes(self, world_id, label, filters=None):
        self.reads.append(("find_nodes", label))
        return super().find_nodes(world_id, label, filters)

    def get_edges(self, world_id, types=None):
        self.reads.append(("get_edges", ""))
        return super().get_edges(world_id, types)


class _DraftLLM:
    def structured(self, prompt, schema, *, system=None):
        return schema.model_validate(
            {"npcs": [{"name": "Ada", "role": "miller", "description": "d"}]}
        )


def _world():
    graph, search = _CountingGraph(), InMemorySearchRepository()
    cache = WorldCache(WorldLoader(graph))
    town = Region(world_id="w", name="Riverton", level=RegionLevel.TOWN, provenance=_prov())
    hollow = Region(world_id="w", name="Hollow", level=RegionLevel.TOWN, provenance=_prov())
    fact = Knowledge(world_id="w", statement="the mill turns", title="mill", provenance=_prov())
    prior = WikiPrior(
        world_id="w",
        prior_type=PriorType.FACT,
        condition="river",
        effect="trade",
        provenance=_prov(),
    )
    road = [
        ConnectionEdge(
            world_id="w",
            source_region_id=a.id,
            target_region_id=b.id,
            kind=ConnectionKind.ROUTE,
            weight=0.6,
            wiki_prior_ref=prior.id,
            provenance=_prov(),
        )
        for a, b in ((town, hollow), (hollow, town))
    ]
    ada = NPC(
        world_id="w",
        name="Ada",
        role="r",
        description="d",
        home_region_id=town.id,
        provenance=_prov(),
    )
    persist_graph(
        graph,
        search,
        None,
        "w",
        regions=[town, hollow],
        knowledge=[fact],
        connections=road,
        priors=[prior],
        npcs=[ada],
        scopes=[ScopeLink(world_id="w", knowledge_id=fact.id, region_id=town.id)],
        meta=WorldMeta(id="w", name="W"),
    )
    world = WorldContainer(
        cache=cache,
        editors=Editors.assemble(graph, search, cache=cache),
        catalog=WorldCatalog(graph),
        exporter=None,
        importer=None,
        demo=None,
        wiki_admin=WikiAdmin(graph, search, cache=cache),
        npc_drafts=NpcDraftService(_DraftLLM(), cache),
    )
    play = play_container()
    client = TestClient(create_app(world=world, play=play))
    return (
        client,
        play,
        graph,
        search,
        {"town": town, "hollow": hollow, "fact": fact, "prior": prior, "ada": ada},
    )


def _player_in(play, region_id: str) -> str:
    session = play.repo.create_session("w")
    play.repo.create_player(Player(session_id=session.id, name="Ann", region_id=region_id))
    return session.id


# --------------------------------------------------------------------------- #
def test_editor_view_lists_children_connections_knowledge_and_npcs() -> None:
    client, _play, _g, _s, w = _world()
    r = client.get(f"/api/world/worlds/w/regions/{w['town'].id}/editor")
    assert r.status_code == 200
    body = r.json()
    assert body["region"]["name"] == "Riverton" and [n["name"] for n in body["npcs"]] == ["Ada"]
    (conn,) = body["connections"]
    assert conn["other_region_name"] == "Hollow" and conn["prior"]["effect"] == "trade"
    (k,) = body["knowledge"]
    assert k["knowledge"]["title"] == "mill" and "statement_ko" in k["knowledge"]
    assert client.get("/api/world/worlds/w/regions/nope/editor").status_code == 404


def test_region_create_replace_and_checks() -> None:
    client, _play, _g, _s, w = _world()
    mill = Region(
        world_id="w",
        name="Mill",
        level=RegionLevel.DISTRICT,
        parent_id=w["town"].id,
        provenance=_prov(),
    )
    assert client.post("/api/world/worlds/w/regions", json=mill.model_dump()).status_code == 201
    assert client.post("/api/world/worlds/w/regions", json=mill.model_dump()).status_code == 400
    town = w["town"].model_copy(update={"parent_id": mill.id})  # under its own child
    r = client.put(f"/api/world/worlds/w/regions/{town.id}", json=town.model_dump())
    assert r.status_code == 400
    r = client.put(f"/api/world/worlds/w/regions/{mill.id}", json=w["town"].model_dump())
    assert r.status_code == 400  # path and body ids differ (BR-U3-5)
    orphan = Region(
        world_id="w", name="O", level=RegionLevel.TOWN, parent_id="nope", provenance=_prov()
    )
    assert client.post("/api/world/worlds/w/regions", json=orphan.model_dump()).status_code == 404


def test_region_delete_is_refused_where_a_player_stands() -> None:
    client, play, graph, _s, w = _world()
    sid = _player_in(play, w["town"].id)
    plan = client.get(f"/api/world/worlds/w/regions/{w['town'].id}/delete-plan").json()
    assert plan["blocked_by_sessions"] == [sid] and [n["name"] for n in plan["npcs"]] == ["Ada"]
    r = client.delete(f"/api/world/worlds/w/regions/{w['town'].id}")
    assert r.status_code == 409 and r.json()["detail"]["session_ids"] == [sid]
    assert graph.get_node("w", w["town"].id) is not None  # nothing deleted


def test_region_delete_waits_for_no_turn_and_holds_the_sessions() -> None:
    client, play, graph, _s, w = _world()
    sid = _player_in(play, w["hollow"].id)
    play.guard.acquire(sid, "run")
    try:
        r = client.delete(f"/api/world/worlds/w/regions/{w['town'].id}")
    finally:
        play.guard.release(sid)
    assert r.status_code == 409 and "turn in progress" in r.json()["detail"]

    regions = client.app.state.containers.world.editors.regions
    original = regions.delete_region
    tries: list[str] = []

    def during(*args, **kwargs):  # a move (a turn) tries to start mid-delete
        try:
            play.guard.acquire(sid, "move")
            tries.append("started")
            play.guard.release(sid)
        except Exception as exc:
            tries.append(type(exc).__name__)
        return original(*args, **kwargs)

    object.__setattr__(regions, "delete_region", during)
    r = client.delete(f"/api/world/worlds/w/regions/{w['town'].id}")
    assert r.status_code == 200 and tries == ["TurnInProgressError"]
    assert set(r.json()["deleted_ids"]) == {w["town"].id, w["ada"].id}
    assert graph.get_node("w", w["town"].id) is None


def test_connections_save_change_kind_and_delete() -> None:
    client, _play, _g, _s, w = _world()
    a, b = w["town"].id, w["hollow"].id
    body = {
        "world_id": "w",
        "source_region_id": a,
        "target_region_id": b,
        "kind": "river",
        "weight": 0.4,
        "provenance": {"source": "input"},
    }
    r = client.put("/api/world/worlds/w/connections", json=body)
    assert r.status_code == 200 and len(r.json()) == 2
    moved = {**body, "kind": "blocked", "previous_kind": "river"}
    assert client.put("/api/world/worlds/w/connections", json=moved).status_code == 200
    r = client.delete("/api/world/worlds/w/connections", params={"a": b, "b": a, "kind": "blocked"})
    assert r.status_code == 200 and r.json() == {"deleted": 2}
    r = client.delete("/api/world/worlds/w/connections", params={"a": a, "b": b, "kind": "river"})
    assert r.status_code == 404
    self_loop = {**body, "target_region_id": a}
    assert client.put("/api/world/worlds/w/connections", json=self_loop).status_code == 400


def test_a_kind_change_keeps_the_pair_fields_and_writes_nothing_else() -> None:
    """U3 review #3 (BR-U3-11): with ``previous_kind`` only the kind changes. The body's
    other fields (no rationale or prior, another provenance) are not written over the
    pair, and the save is one move (upsert + delete), not a second replace."""
    client, _play, graph, _s, w = _world()
    a, b = w["town"].id, w["hollow"].id
    body = {
        "world_id": "w",
        "source_region_id": a,
        "target_region_id": b,
        "kind": "blocked",
        "weight": 0.2,
        "rationale": "the pass is snowed in",
        "wiki_prior_ref": "prior-pass",
        "provenance": {"source": "inferred", "generated_by": "demo-author"},
    }
    assert client.put("/api/world/worlds/w/connections", json=body).status_code == 200
    moved = {
        "world_id": "w",
        "source_region_id": a,
        "target_region_id": b,
        "kind": "adjacent",
        "weight": 0.6,
        "provenance": {"source": "input", "generated_by": "designer"},
        "previous_kind": "blocked",
    }
    r = client.put("/api/world/worlds/w/connections", json=moved)
    assert r.status_code == 200
    pair = r.json()
    assert {e["kind"] for e in pair} == {"adjacent"} and len(pair) == 2
    for e in pair:
        assert e["weight"] == 0.2 and e["rationale"] == "the pass is snowed in"
        assert e["wiki_prior_ref"] == "prior-pass"
        assert e["provenance"]["source"] == "inferred"
    stored = [e for e in graph.get_edges("w", ["CONNECTED_TO"]) if e.properties["kind"] != "route"]
    assert sorted(e.properties["kind"] for e in stored) == ["adjacent", "adjacent"]
    assert all(e.properties.get("rationale") == "the pass is snowed in" for e in stored)


def test_knowledge_add_edit_scopes_unscoped_and_delete() -> None:
    client, _play, graph, search, w = _world()
    new = Knowledge(world_id="w", statement="a dry well", title="well", provenance=_prov())
    r = client.post(
        f"/api/world/worlds/w/regions/{w['hollow'].id}/knowledge", json=new.model_dump()
    )
    assert r.status_code == 201
    edited = new.model_copy(update={"statement": "a wet well"})
    assert (
        client.put(f"/api/world/worlds/w/knowledge/{new.id}", json=edited.model_dump()).status_code
        == 200
    )
    r = client.put(f"/api/world/worlds/w/knowledge/{new.id}/scopes", json={"region_ids": []})
    assert r.status_code == 200 and r.json() == {"region_ids": []}
    unscoped = client.get("/api/world/worlds/w/knowledge/unscoped").json()
    assert [k["id"] for k in unscoped] == [new.id] and "statement_ko" in unscoped[0]
    assert client.delete(f"/api/world/worlds/w/knowledge/{new.id}").status_code == 204
    assert ("w", new.id) not in search.docs
    assert client.delete(f"/api/world/worlds/w/knowledge/{new.id}").status_code == 404


def test_npcs_and_drafts() -> None:
    client, _play, _g, _s, w = _world()
    bo = NPC(
        world_id="w",
        name="Bo",
        role="ferryman",
        description="d",
        home_region_id=w["hollow"].id,
        provenance=_prov(),
    )
    assert client.post("/api/world/worlds/w/npcs", json=bo.model_dump()).status_code == 201
    moved = bo.model_copy(update={"home_region_id": "nope"})
    assert (
        client.put(f"/api/world/worlds/w/npcs/{bo.id}", json=moved.model_dump()).status_code == 404
    )
    assert client.delete(f"/api/world/worlds/w/npcs/{bo.id}").status_code == 204
    r = client.post(f"/api/world/worlds/w/regions/{w['town'].id}/npc-drafts")
    assert r.status_code == 200 and [d["name"] for d in r.json()["drafts"]] == ["Ada"]
    r = client.post(f"/api/world/worlds/w/regions/{w['town'].id}/npc-drafts", params={"n": 4})
    assert r.status_code == 400


def test_priors_refs_and_delete() -> None:
    client, _play, _g, _s, w = _world()
    assert [p["id"] for p in client.get("/api/world/worlds/w/priors").json()] == [w["prior"].id]
    refs = client.get("/api/world/worlds/w/prior-refs").json()
    assert len(refs["usages"][0]["connections"]) == 1 and refs["broken"] == []
    assert client.delete(f"/api/world/worlds/w/priors/{w['prior'].id}").status_code == 204
    refs = client.get("/api/world/worlds/w/prior-refs").json()
    assert refs["usages"] == [] and refs["broken"][0]["ref_id"] == w["prior"].id
    assert client.delete(f"/api/world/worlds/w/priors/{w['prior'].id}").status_code == 404


def test_world_list_reads_no_snapshot_and_cache_hits_read_only_the_version() -> None:
    """nfr §1 NFR-3 ④ and ⑤ (〔Step 1.3 정정〕 R-02)."""
    client, _play, graph, _s, w = _world()
    graph.reads.clear()
    assert client.get("/api/world/worlds").status_code == 200
    assert graph.reads == [("find_nodes", "WorldMeta"), ("find_nodes", "Region")]
    client.get(f"/api/world/worlds/w/regions/{w['town'].id}/editor")  # warms the cache
    graph.reads.clear()
    client.get(f"/api/world/worlds/w/regions/{w['town'].id}/editor")
    assert graph.reads == [("find_nodes", "WorldMeta")]  # the version check, no load


def test_llm_free_world_edits_and_augments_but_drafts_answer_503() -> None:
    """NFR-4: without an LLM the editor and the Q&A work; NPC drafts are 503."""
    graph, search = InMemoryGraphRepository(), InMemorySearchRepository()
    cache = WorldCache(WorldLoader(graph))
    town = Region(world_id="w", name="Riverton", level=RegionLevel.TOWN, provenance=_prov())
    persist_graph(graph, search, None, "w", regions=[town], meta=WorldMeta(id="w", name="W"))
    shared = SharedContainer(settings=Settings(), graph=graph, search=search, llm=None)
    knowledge = KnowledgeContainer(
        loader=WorldLoader(graph), cache=cache, query=None, params=None  # type: ignore[arg-type]
    )
    world = assemble_world(shared, knowledge)
    assert world.builder is None and world.npc_drafts is None and world.augmentation is not None
    client = TestClient(create_app(world=world))
    edited = town.model_copy(update={"description": "a river town"})
    assert (
        client.put(f"/api/world/worlds/w/regions/{town.id}", json=edited.model_dump()).status_code
        == 200
    )
    assert client.post(f"/api/world/worlds/w/regions/{town.id}/npc-drafts").status_code == 503
    run = client.post("/api/world/worlds/w/augmentation/runs")
    assert run.status_code == 200 and run.json()["llm_calls"] == 0
