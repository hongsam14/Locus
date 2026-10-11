"""V7 carry-over: a rebuild keeps the world's NPCs and event seeds (BR-V7-13..15, PBT-V7-4)."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from locus.knowledge.loader import NPC_HOME_DANGLING, SEED_REGION_DANGLING
from locus.shared.models import (
    NPC,
    BuildReport,
    BuildWarning,
    EventSeed,
    KnowledgeGraph,
    Provenance,
    Region,
    RegionLevel,
    RegionTopology,
    SourceKind,
    WorldSnapshot,
)
from locus.world.carry_over import carry_over, region_key

_PROV = Provenance(source=SourceKind.INPUT)


def _region(rid: str, name: str, level=RegionLevel.TOWN, parent: str | None = None) -> Region:
    return Region(id=rid, world_id="w", name=name, level=level, parent_id=parent, provenance=_PROV)


def _npc(nid: str, home: str) -> NPC:
    return NPC(
        id=nid,
        world_id="w",
        name=f"npc {nid}",
        role="miller",
        description="d",
        home_region_id=home,
        provenance=_PROV,
    )


def _seed(sid: str, region: str) -> EventSeed:
    return EventSeed(
        id=sid,
        world_id="w",
        region_id=region,
        title=f"seed {sid}",
        category="disaster",
        magnitude=0.5,
        provenance=_PROV,
    )


def _old(regions, npcs=(), seeds=(), load_warnings=()) -> WorldSnapshot:
    return WorldSnapshot(
        world_id="w",
        kg=KnowledgeGraph(world_id="w"),
        topo=RegionTopology(world_id="w", regions=list(regions)),
        npcs=list(npcs),
        event_seeds=list(seeds),
        load_warnings=list(load_warnings),
    )


def test_region_key_normalizes_width_case_and_spaces() -> None:
    assert region_key("  Ｍill\tTown ", "town") == region_key("mill town", RegionLevel.TOWN)
    assert region_key("Mill", "town") != region_key("Mill", "district")


def test_an_npc_and_a_seed_move_to_the_region_of_the_same_name() -> None:
    old = _old([_region("o1", "Mill Town")], [_npc("n1", "o1")], [_seed("s1", "o1")])
    out = carry_over(old, [_region("n-1", "mill  town")], "w")
    assert [(n.id, n.home_region_id, n.role) for n in out.npcs] == [("n1", "n-1", "miller")]
    assert [(s.id, s.region_id, s.title) for s in out.seeds] == [("s1", "n-1", "seed s1")]
    assert out.warnings == []


def test_a_renamed_region_leaves_its_npc_behind_with_a_warning() -> None:
    old = _old([_region("o1", "Mill")], [_npc("n1", "o1")], [_seed("s1", "o1")])
    out = carry_over(old, [_region("n-1", "Windmill")], "w")
    assert out.npcs == [] and out.seeds == []
    assert [(w.stage, w.severity, w.item_id) for w in out.warnings] == [
        ("carry-over", "warning", "n1"),
        ("carry-over", "warning", "s1"),
    ]
    assert out.warnings[0].message == (
        "NPC npc n1 was not carried over: no region named Mill (town) in the new world"
    )


def test_two_regions_of_one_name_are_told_apart_by_their_parents() -> None:
    old = _old(
        [
            _region("o-north", "North", RegionLevel.PROVINCE),
            _region("o-south", "South", RegionLevel.PROVINCE),
            _region("o-mill", "Mill", parent="o-south"),
        ],
        [_npc("n1", "o-mill")],
    )
    new = [
        _region("x-north", "North", RegionLevel.PROVINCE),
        _region("x-south", "South", RegionLevel.PROVINCE),
        _region("x-mill-n", "Mill", parent="x-north"),
        _region("x-mill-s", "Mill", parent="x-south"),
    ]
    assert [n.home_region_id for n in carry_over(old, new, "w").npcs] == ["x-mill-s"]


def test_two_regions_the_parents_cannot_tell_apart_are_a_warning() -> None:
    old = _old([_region("o-mill", "Mill")], [_npc("n1", "o-mill")])
    out = carry_over(old, [_region("a", "Mill"), _region("b", "Mill")], "w")
    assert out.npcs == []
    assert out.warnings[0].message == "NPC npc n1 was not carried over: 2 regions named Mill (town)"


def test_what_the_loader_dropped_is_reported_too() -> None:
    """FD review R-10: an NPC or seed whose region was already gone never reached the
    snapshot; the replace loses it all the same, so it is named."""
    dropped = [
        BuildWarning(
            stage="load", item_id="n9", message=f"{NPC_HOME_DANGLING}: dangling reference"
        ),
        BuildWarning(
            stage="load", item_id="s9", message=f"{SEED_REGION_DANGLING}: dangling reference"
        ),
        BuildWarning(stage="load", item_id="k1", message="SCOPED_TO: dangling reference"),
    ]
    out = carry_over(_old([_region("o1", "Mill")], load_warnings=dropped), [], "w")
    assert [(w.item_id, w.message) for w in out.warnings] == [
        ("n9", "NPC n9 was not carried over: its region is not in the old world"),
        ("s9", "Event seed s9 was not carried over: its region is not in the old world"),
    ]


def test_pbt_02_a_report_with_carried_counts_survives_json() -> None:
    report = BuildReport(world_id="w", carried_npcs=2, carried_seeds=1)
    back = BuildReport.model_validate_json(report.model_dump_json(exclude={"ok"}))
    assert back == report and (back.carried_npcs, back.carried_seeds) == (2, 1)


# --------------------------------------------------------------------------- #
# PBT-V7-4: everything is carried or named once, onto new regions, in any order
# --------------------------------------------------------------------------- #
_NAMES = ["Mill", "mill", "Ford", "Keep"]
_LEVELS = [RegionLevel.TOWN, RegionLevel.DISTRICT]


@st.composite
def _rebuilds(draw):
    def regions(prefix: str) -> list[Region]:
        out: list[Region] = []
        for i in range(draw(st.integers(min_value=0, max_value=5))):
            parent = draw(st.none() | st.sampled_from([r.id for r in out])) if out else None
            out.append(
                _region(
                    f"{prefix}{i}",
                    draw(st.sampled_from(_NAMES)),
                    draw(st.sampled_from(_LEVELS)),
                    parent,
                )
            )
        return out

    old_regions, new_regions = regions("o"), regions("n")
    homes = [r.id for r in old_regions] + ["gone"]  # "gone": an already broken reference
    npcs = [
        _npc(f"npc{i}", draw(st.sampled_from(homes)))
        for i in range(draw(st.integers(min_value=0, max_value=4)))
    ]
    seeds = [
        _seed(f"seed{i}", draw(st.sampled_from(homes)))
        for i in range(draw(st.integers(min_value=0, max_value=3)))
    ]
    dropped = [
        BuildWarning(stage="load", item_id=f"lost{i}", message=f"{what}: dangling reference")
        for i, what in enumerate(
            draw(st.lists(st.sampled_from([NPC_HOME_DANGLING, SEED_REGION_DANGLING]), max_size=2))
        )
    ]
    return _old(old_regions, npcs, seeds, dropped), new_regions


@settings(max_examples=150, deadline=None)
@given(case=_rebuilds(), data=st.data())
def test_pbt_v7_4_each_item_is_carried_or_named_once(case, data) -> None:
    old, new_regions = case
    out = carry_over(old, new_regions, "w")
    dropped = len(old.load_warnings)
    assert len(out.npcs) + len(out.seeds) + len(out.warnings) == (
        len(old.npcs) + len(old.event_seeds) + dropped
    )
    new_by_id = {r.id: r for r in new_regions}
    old_by_id = old.regions_by_id

    def same_key(old_id: str, new_id: str) -> bool:  # name and level both (review #8)
        o, n = old_by_id[old_id], new_by_id[new_id]
        return region_key(o.name, o.level) == region_key(n.name, n.level)

    old_npc = {n.id: n for n in old.npcs}
    old_seed = {s.id: s for s in old.event_seeds}
    assert all(same_key(old_npc[n.id].home_region_id, n.home_region_id) for n in out.npcs)
    assert all(same_key(old_seed[s.id].region_id, s.region_id) for s in out.seeds)

    shuffled = old.model_copy(
        update={
            "npcs": data.draw(st.permutations(old.npcs)),
            "event_seeds": data.draw(st.permutations(old.event_seeds)),
        }
    )
    again = carry_over(shuffled, data.draw(st.permutations(new_regions)), "w")
    assert {(n.id, n.home_region_id) for n in again.npcs} == {
        (n.id, n.home_region_id) for n in out.npcs
    }
    assert {(s.id, s.region_id) for s in again.seeds} == {(s.id, s.region_id) for s in out.seeds}
    assert sorted(w.message for w in again.warnings) == sorted(w.message for w in out.warnings)


# --------------------------------------------------------------------------- #
# Code review 01 (#2, #8, #11, #21)
# --------------------------------------------------------------------------- #
def test_a_region_of_the_same_name_at_another_level_is_not_a_match() -> None:  # review #8
    old = _old([_region("o1", "Mill", RegionLevel.TOWN)], [_npc("n1", "o1")])
    out = carry_over(old, [_region("x1", "Mill", RegionLevel.DISTRICT)], "w")
    assert out.npcs == [] and "no region named Mill (town)" in out.warnings[0].message


def test_a_name_shared_in_the_old_world_needs_its_parent_too() -> None:  # review #11
    """Two Mills in the old world; the new one keeps only the southern Mill. The southern
    miller goes there; the northern one is named, not moved south."""
    old = _old(
        [
            _region("o-n", "North", RegionLevel.PROVINCE),
            _region("o-s", "South", RegionLevel.PROVINCE),
            _region("o-mill-n", "Mill", parent="o-n"),
            _region("o-mill-s", "Mill", parent="o-s"),
        ],
        [_npc("north", "o-mill-n"), _npc("south", "o-mill-s")],
    )
    new = [
        _region("x-n", "North", RegionLevel.PROVINCE),
        _region("x-s", "South", RegionLevel.PROVINCE),
        _region("x-mill-s", "Mill", parent="x-s"),
    ]
    out = carry_over(old, new, "w")
    assert [(n.id, n.home_region_id) for n in out.npcs] == [("south", "x-mill-s")]
    assert out.warnings[0].message == (
        "NPC npc north was not carried over: "
        "no region named Mill (town) under its old parent in the new world"
    )


def test_two_candidates_neither_under_the_old_parent_are_counted() -> None:  # review #21
    old = _old(
        [_region("o-p", "Old"), _region("o-mill", "Mill", parent="o-p")], [_npc("n", "o-mill")]
    )
    new = [
        _region("a", "A"),
        _region("b", "B"),
        _region("m1", "Mill", parent="a"),
        _region("m2", "Mill", parent="b"),
    ]
    out = carry_over(old, new, "w")
    assert out.warnings[0].message == "NPC npc n was not carried over: 2 regions named Mill (town)"


def test_an_npc_or_seed_the_load_could_not_read_is_named() -> None:  # review #2
    dropped = [
        BuildWarning(stage="load", item_id="n8", message="NPC: 1 validation error for NPC"),
        BuildWarning(stage="load", item_id="s8", message="EventSeed: title too long"),
    ]
    out = carry_over(_old([], load_warnings=dropped), [], "w")
    assert [w.message for w in out.warnings] == [
        "NPC n8 was not carried over: it could not be read from the old world",
        "Event seed s8 was not carried over: it could not be read from the old world",
    ]
