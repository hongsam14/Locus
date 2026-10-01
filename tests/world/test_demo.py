"""Demo worlds are data (U8 BLM §1, BR-U8-1..11, TP-U8-4, EX-9..11).

U8 intended change (BR-U8-1, Q1=C): the packaged demo is Emberleaf Isle, found only
through the manifest; the old Aldermoor is a test fixture (``tests/fixtures/aldermoor``).
The tests that loaded Aldermoor here now load the manifest's demo.
"""

from __future__ import annotations

import json
import shutil
from collections import deque
from pathlib import Path

import pytest

from locus.knowledge.cache import WorldCache
from locus.knowledge.consensus import compute_consensus
from locus.knowledge.loader import WorldLoader
from locus.knowledge.propagation import best_path_weights
from locus.play.rumor.spread import neighbour_map, passable_both_ways
from locus.shared.config.tuning import KnowledgeTuning, PlayTuning
from locus.world.demo import WORLDS_DIR, DemoWorlds, check_packaged
from locus.world.worldfile import WorldFileImporter
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "aldermoor"


def _demos(worlds_dir: Path = WORLDS_DIR, builder=None):
    graph = InMemoryGraphRepository()
    cache = WorldCache(WorldLoader(graph))
    importer = WorldFileImporter(graph, InMemorySearchRepository(), None, cache)
    return DemoWorlds(importer, builder, worlds_dir=worlds_dir), graph, cache


def _demo_snapshot():
    demos, _graph, cache = _demos()
    info = demos.list()[0]
    assert demos.load(info.name, info.name).ok  # its own id: no remapping
    return info, cache.get(info.name)


# --------------------------------------------------------------------------- #
# the manifest (BR-U8-1..5)
# --------------------------------------------------------------------------- #
def test_the_package_lists_its_demo_from_the_manifest_with_no_problem() -> None:
    demos = DemoWorlds()  # no importer: listing and checking need none
    assert [d.name for d in demos.list()] == ["emberleaf"]
    assert demos.problems == [] and check_packaged() == []
    info = demos.info("emberleaf")
    assert info.has_sources and info.credits and "Nexon" in info.credits
    with pytest.raises(RuntimeError):
        demos.load("emberleaf", "w")
    with pytest.raises(LookupError):
        demos.info("nope")


def test_loading_the_demo_calls_no_llm_and_replaces_instead_of_duplicating() -> None:
    demos, graph, cache = _demos()
    report = demos.load("emberleaf", "w")
    assert report.ok and report.remapped is True  # file world "emberleaf" -> target "w"
    snap = cache.get("w")
    assert len(snap.topo.regions) == 12 and len(snap.event_seeds) == 3
    assert snap.meta is not None and snap.meta.name == "Emberleaf Isle"
    again = demos.load("emberleaf", "w")  # replace, not duplicate (RE A3, BR-U8-5)
    assert again.ok and again.replaced is True
    assert len(cache.get("w").topo.regions) == 12 and graph.list_world_ids() == ["w"]
    assert demos.load("emberleaf", "emberleaf").remapped is False  # the default world id


def test_sources_are_read_from_the_manifest_and_build_through_the_builder() -> None:
    class _Builder:
        def __init__(self) -> None:
            self.calls: list = []

        def build(self, world_id, inputs, *, replace=True):
            self.calls.append((world_id, inputs, replace))
            return "report"

    builder = _Builder()
    demos, _g, _c = _demos(builder=builder)
    inputs = demos.sources("emberleaf")
    assert inputs.name == "Emberleaf Isle" and inputs.map_images == []
    assert "Glimmerrun" in inputs.memos[0]
    assert {r["name"] for r in inputs.structured_maps[0]["regions"]} >= {"Sylvarch", "Ironcrag"}
    assert demos.build_from_sources("emberleaf", "w2") == "report"
    assert builder.calls[0][0] == "w2" and builder.calls[0][2] is True
    assert DemoWorlds().build_from_sources.__doc__  # the source build is not the World File


def _workdir(tmp_path: Path, entries: list[dict]) -> Path:
    shutil.copy(WORLDS_DIR / "emberleaf.world.json", tmp_path / "emberleaf.world.json")
    (tmp_path / "src").mkdir()
    shutil.copy(FIXTURE / "memo.txt", tmp_path / "src" / "memo.txt")
    shutil.copy(FIXTURE / "map.png", tmp_path / "src" / "map.png")
    (tmp_path / "manifest.json").write_text(json.dumps(entries), encoding="utf-8")
    return tmp_path


def _entry(**kw) -> dict:
    base = {
        "name": "isle",
        "title": "Isle",
        "file": "emberleaf.world.json",
        "start_region_id": "region-saltwake",
    }
    return {**base, **kw}


def test_ex11_a_bad_entry_is_left_out_and_the_others_stay(tmp_path: Path) -> None:
    """EX-11 (BR-U8-2): each check leaves out only its own entry, with a problem."""
    work = _workdir(
        tmp_path,
        [
            _entry(),
            _entry(name="no-start", start_region_id="region-nowhere"),
            _entry(name="cut-off", start_region_id="region-emberleaf"),  # no connection
            _entry(name="escape", file="../outside.json"),
            _entry(name="lost-source", sources={"memos": ["src/missing.md"]}),
            _entry(),  # listed twice
            {"name": "Bad Name", "title": "x", "file": "f", "start_region_id": "r"},
        ],
    )
    demos = DemoWorlds(worlds_dir=work)
    assert [d.name for d in demos.list()] == ["isle"]
    assert len(demos.problems) == 6
    text = " ".join(demos.problems)
    for word in ("not in", "no passable connection", "outside the demo folder", "missing", "twice"):
        assert word in text


def test_a_demo_without_sources_cannot_build_and_images_are_read_when_asked(
    tmp_path: Path,
) -> None:
    work = _workdir(
        tmp_path,
        [
            _entry(),
            _entry(
                name="imaged", sources={"memos": ["src/memo.txt"], "map_images": ["src/map.png"]}
            ),
        ],
    )
    demos = DemoWorlds(worlds_dir=work)
    with pytest.raises(LookupError, match="no sources"):
        demos.sources("isle")  # BR-U8-4 -> 404 at the API
    with_map = demos.sources("imaged")
    assert len(with_map.map_images) == 1 and with_map.map_images[0].startswith("iVBOR")
    assert demos.sources("imaged", include_map=False).map_images == []


# --------------------------------------------------------------------------- #
# Emberleaf content (TP-U8-4, BR-U8-6..11)
# --------------------------------------------------------------------------- #
FORBIDDEN = (
    "maple",
    "victoria",
    "henesys",
    "ellinia",
    "perion",
    "kerning",
    "lith harbor",
    "sleepywood",
    "nautilus",
    "black mage",
    "nexon cash",
)


def test_tp_u8_4_the_demo_has_the_promised_shape() -> None:
    _info, snap = _demo_snapshot()
    regions = snap.topo.regions
    by_id = snap.regions_by_id
    assert 10 <= len(regions) <= 15
    depth = {r.id: 0 for r in regions if r.parent_id is None}
    while len(depth) < len(regions):
        for r in regions:
            if r.parent_id in depth and r.id not in depth:
                depth[r.id] = depth[r.parent_id] + 1
    assert max(depth.values()) == 2  # three levels (BR-U8-6)
    leaves = [r for r in regions if not any(o.parent_id == r.id for o in regions)]
    for r in regions:
        n = len(snap.npcs_by_region.get(r.id, []))
        assert (1 <= n <= 3) if r in leaves else n == 0, r.name
    kinds = {str(c.kind) for c in snap.topo.connections}
    assert {"river", "route", "blocked"} <= kinds
    pairs = {(c.source_region_id, c.target_region_id, str(c.kind)) for c in snap.topo.connections}
    assert all((b, a, k) in pairs for a, b, k in pairs)  # every connection is a pair
    direct: dict[str, int] = {}
    for s in snap.kg.scopes:
        direct[s.region_id] = direct.get(s.region_id, 0) + 1
    assert all(direct.get(r.id, 0) >= 2 for r in leaves)
    assert 1 <= sum(k.is_global for k in snap.kg.knowledge) <= 2
    seeds = snap.event_seeds
    assert 2 <= len(seeds) <= 3
    assert len({s.region_id for s in seeds}) == len(seeds)
    assert len({str(s.category) for s in seeds}) == len(seeds)
    assert all(by_id[s.region_id] in leaves for s in seeds)


def test_every_town_is_reached_from_the_start_and_each_blocked_pair_has_a_way_round() -> None:
    info, snap = _demo_snapshot()
    near = neighbour_map(passable_both_ways(snap))
    start = info.start_region_id

    def hops(a: str) -> dict[str, int]:
        seen, queue = {a: 0}, deque([a])
        while queue:
            x = queue.popleft()
            for y in near.get(x, {}):
                if y not in seen:
                    seen[y] = seen[x] + 1
                    queue.append(y)
        return seen

    leaves = [
        r.id for r in snap.topo.regions if not any(o.parent_id == r.id for o in snap.topo.regions)
    ]
    assert set(leaves) <= set(hops(start))
    for c in snap.topo.connections:
        if str(c.kind) == "blocked":
            assert c.target_region_id in hops(c.source_region_id)  # a way round


def _ids(snap) -> dict[str, str]:
    return {r.name: r.id for r in snap.topo.regions}


TABLE = {  # domain-entities §5.2: max-product weights over every connection
    "Ambermeadow": {
        "Sylvarch": 1.0,
        "Saltwake Harbor": 1.0,
        "Gutterlight": 0.6,
        "Sunstrand": 0.8,
        "Hollowdeep": 0.4,
        "Ironcrag": 0.204,
        "Ashen Dig": 0.163,
    },
    "Saltwake Harbor": {
        "Sylvarch": 1.0,
        "Ambermeadow": 1.0,
        "Gutterlight": 0.6,
        "Sunstrand": 0.8,
        "Hollowdeep": 0.4,
        "Ironcrag": 0.204,
        "Ashen Dig": 0.163,
    },
    "Gutterlight": {
        "Sylvarch": 0.6,
        "Ambermeadow": 0.6,
        "Saltwake Harbor": 0.6,
        "Sunstrand": 0.48,
        "Hollowdeep": 0.5,
        "Ironcrag": 0.34,
        "Ashen Dig": 0.272,
    },
    "Ashen Dig": {
        "Sylvarch": 0.163,
        "Ambermeadow": 0.163,
        "Saltwake Harbor": 0.163,
        "Gutterlight": 0.272,
        "Sunstrand": 0.131,
        "Hollowdeep": 0.2,
        "Ironcrag": 0.8,
    },
    "Ironcrag": {
        "Sylvarch": 0.204,
        "Ambermeadow": 0.204,
        "Saltwake Harbor": 0.204,
        "Gutterlight": 0.34,
        "Sunstrand": 0.163,
        "Hollowdeep": 0.17,
        "Ashen Dig": 0.8,
    },
}


def test_the_path_weights_are_the_designed_table() -> None:
    _info, snap = _demo_snapshot()
    ids = _ids(snap)
    for origin, row in TABLE.items():
        got = best_path_weights(ids[origin], snap.topo.connections)
        for town, want in row.items():
            assert round(got.get(ids[town], 0.0), 3) == want, (origin, town)


def test_ex9_river_towns_share_town_knowledge_and_ironcrag_hears_the_lowlands() -> None:
    """EX-9 (BR-U8-11, FD R-13): the hearsay list is every town between the thresholds."""
    _info, snap = _demo_snapshot()
    ids = _ids(snap)
    names = {v: k for k, v in ids.items()}
    tuning = KnowledgeTuning()
    town_of = {s.knowledge_id: names[s.region_id] for s in snap.kg.scopes}

    def view(town: str):
        return compute_consensus(ids[town], snapshot=snap)

    saltwake = view("Saltwake Harbor")
    propagated_from = {town_of[k.knowledge_id] for k in saltwake.propagated}
    assert {"Sylvarch", "Ambermeadow"} <= propagated_from
    ironcrag = view("Ironcrag")
    heard_from = {town_of[k.knowledge_id] for k in ironcrag.hearsay if k.knowledge_id in town_of}
    expected = {
        town
        for town, w in TABLE["Ironcrag"].items()
        if tuning.hearsay_min <= w < tuning.propagate_min
    }
    assert heard_from == expected
    assert "Ashen Dig" in {town_of[k.knowledge_id] for k in ironcrag.propagated}


def test_ex10_a_deed_in_ambermeadow_needs_three_turns_to_reach_ironcrag() -> None:
    """EX-10 (BR-U8-11): one hop per turn over passable connections — Saltwake and
    Sylvarch after one turn, Ironcrag not before the third, at a weight above the bar."""
    _info, snap = _demo_snapshot()
    ids = _ids(snap)
    edges = passable_both_ways(snap)
    near = neighbour_map(edges)
    hops, queue = {ids["Ambermeadow"]: 0}, deque([ids["Ambermeadow"]])
    while queue:
        x = queue.popleft()
        for y in near.get(x, {}):
            if y not in hops:
                hops[y] = hops[x] + 1
                queue.append(y)
    assert hops[ids["Saltwake Harbor"]] == 1 and hops[ids["Sylvarch"]] == 1
    assert hops[ids["Ironcrag"]] == 3
    reach = best_path_weights(ids["Ambermeadow"], edges)
    assert reach[ids["Ironcrag"]] >= PlayTuning().spread_min_weight


def test_the_demo_uses_no_name_from_the_game_it_borrows_its_mood_from() -> None:
    """BR-U8-10 (Q1-2=A): original names and text; the credits line is the one mention."""
    text = (WORLDS_DIR / "emberleaf.world.json").read_text(encoding="utf-8").lower()
    text += (WORLDS_DIR / "emberleaf" / "memo.md").read_text(encoding="utf-8").lower()
    assert [w for w in FORBIDDEN if w in text] == []
