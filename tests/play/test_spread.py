"""U6 deed-rumor spread — the pure planner, the region quota and the decay exemption
(Step 4.6): TP-U6-1/2/8, EX-6/7 arithmetic, the non-best-path weight (code-plan review
R-01) and the rumor-level birth-turn exemption (FD review R-15)."""

from __future__ import annotations

from collections import Counter

from hypothesis import given, settings
from hypothesis import strategies as st

from locus.knowledge.propagation import best_path_weights
from locus.play.models import SessionRumor
from locus.play.rumor.dynamics import decay_support
from locus.play.rumor.spread import is_session_origin, passable_both_ways, plan_spread
from locus.play.turn.quota import RegionQuota
from locus.shared.config.tuning import PlayTuning
from locus.shared.models import ConnectionKind, Provenance, SourceKind
from tests.play.strategies import build_snapshot, deed_rumor, edge, spread_worlds

TUNING = PlayTuning()


def _canonical(region: str) -> SessionRumor:
    return SessionRumor(
        session_id="s",
        region_id=region,
        distorted_from_id="k",
        support=0.9,
        provenance=Provenance(source=SourceKind.SIMULATION),
    )


# --- TP-U6-1: every target obeys the hop rules ----------------------------------- #
@settings(max_examples=120)
@given(world=spread_worlds(), data=st.data())
def test_tp_u6_1_targets_are_passable_unreached_strong_enough_and_more_distorted(world, data):
    ids = sorted(world.regions_by_id)
    origin = data.draw(st.sampled_from(ids))
    here = data.draw(st.sampled_from(ids))
    reached = set(data.draw(st.lists(st.sampled_from(ids), max_size=len(ids))))
    rumor = deed_rumor(
        here, support=data.draw(st.floats(0.0, 1.0)), degree=data.draw(st.floats(0.0, 1.0))
    )
    targets = plan_spread(world, rumor, origin_region_id=origin, reached=reached, tuning=TUNING)
    graph = passable_both_ways(world)
    best = best_path_weights(origin, graph)
    passable_neighbours = {c.target_region_id for c in graph if c.source_region_id == here}
    floor = TUNING.prune_floor + TUNING.support_decay
    for t in targets:
        assert t.region_id in passable_neighbours and t.region_id not in reached
        assert t.weight >= TUNING.spread_min_weight
        assert t.weight <= best.get(t.region_id, 0.0) + 1e-9  # BR-U6-17 (review R-01)
        assert t.degree >= max(rumor.distortion_degree, 1.0 - t.weight) - 1e-9
        assert t.degree <= 1.0 and t.support >= floor
    assert [t.region_id for t in targets] == [
        t.region_id for t in sorted(targets, key=lambda t: (-t.weight, t.region_id))
    ]


def test_tp_u6_1_canonical_rumors_never_spread() -> None:
    world = build_snapshot(["a", "b"], [edge("a", "b", weight=0.9)])
    assert not is_session_origin(_canonical("a"))
    assert (
        plan_spread(world, _canonical("a"), origin_region_id="a", reached=set(), tuning=TUNING)
        == []
    )


# --- TP-U6-2: a pure multi-turn simulation keeps the spread invariants ------------- #
def _simulate(world, seeds, turns, tuning):
    """seeds: (appraisal_id, origin, support). Returns (all rumors, per-turn region counts,
    parent->child pairs)."""
    rumors = []
    origin_of = {}
    reached: dict[str, set[str]] = {}
    for ap, origin, support in seeds:
        rumors.append(deed_rumor(origin, appraisal_id=ap, support=support, degree=0.2))
        origin_of[ap] = origin
        reached.setdefault(ap, set()).add(origin)
    per_turn, pairs = [], []
    graph = passable_both_ways(world)
    for _ in range(turns):
        counts: Counter[str] = Counter()
        born = []
        for parent in sorted(rumors, key=lambda r: (-r.support, r.id)):
            ap = parent.origin_appraisal_id
            for t in plan_spread(
                world,
                parent,
                origin_region_id=origin_of[ap],
                reached=reached[ap],
                tuning=tuning,
                edges=graph,
            ):
                if counts[t.region_id] >= tuning.max_spread_per_region_turn:
                    continue
                child = deed_rumor(t.region_id, appraisal_id=ap, support=t.support, degree=t.degree)
                reached[ap].add(t.region_id)
                counts[t.region_id] += 1
                born.append(child)
                pairs.append((parent, child))
        rumors += born
        per_turn.append(counts)
    return rumors, per_turn, pairs


@settings(max_examples=60)
@given(world=spread_worlds(max_regions=10), data=st.data())
def test_tp_u6_2_no_version_reaches_a_region_twice_and_caps_hold(world, data):
    ids = sorted(world.regions_by_id)
    n = data.draw(st.integers(1, 3))
    seeds = [
        (f"ap{i}", data.draw(st.sampled_from(ids)), data.draw(st.floats(0.1, 0.4)))
        for i in range(n)
    ]
    rumors, per_turn, pairs = _simulate(world, seeds, data.draw(st.integers(1, 6)), TUNING)
    keys = [(r.origin_appraisal_id, r.region_id) for r in rumors]
    assert len(keys) == len(set(keys))  # BR-U6-19
    assert all(c <= TUNING.max_spread_per_region_turn for t in per_turn for c in t.values())
    assert all(child.distortion_degree >= parent.distortion_degree for parent, child in pairs)


# --- EX-6 / EX-7 arithmetic -------------------------------------------------------- #
def test_ex6_a_to_b_then_c_never_across_the_blocked_pass() -> None:
    """A—B 0.6, A—C blocked only, B—C 0.5; salience 1.0 seed = 0.2 × 2 = 0.40."""
    world = build_snapshot(
        ["a", "b", "c"],
        [
            edge("a", "b", weight=0.6),
            edge("a", "c", weight=0.9, kind=ConnectionKind.BLOCKED),
            edge("b", "c", weight=0.5),
        ],
    )
    seed = deed_rumor("a", support=0.40, degree=0.3)
    (to_b,) = plan_spread(world, seed, origin_region_id="a", reached={"a"}, tuning=TUNING)
    assert (to_b.region_id, round(to_b.weight, 6), round(to_b.support, 6)) == ("b", 0.6, 0.32)
    assert to_b.degree >= 0.4 - 1e-9
    at_b = deed_rumor("b", support=to_b.support, degree=to_b.degree)
    (to_c,) = plan_spread(world, at_b, origin_region_id="a", reached={"a", "b"}, tuning=TUNING)
    assert (to_c.region_id, round(to_c.weight, 6), round(to_c.support, 6)) == ("c", 0.3, 0.24)
    assert to_c.degree >= 0.7 - 1e-9
    assert all(
        t.region_id != "c"
        for t in plan_spread(world, seed, origin_region_id="a", reached={"a"}, tuning=TUNING)
    )


def test_ex7_ten_close_regions_offer_nine_hops_at_once() -> None:
    ids = [f"r{i}" for i in range(10)]
    world = build_snapshot(ids, [edge(a, b, weight=0.9) for a in ids for b in ids if a < b])
    seed = deed_rumor("r0", support=0.30)  # salience 0.5 -> 0.2 × 1.5
    targets = plan_spread(world, seed, origin_region_id="r0", reached={"r0"}, tuning=TUNING)
    assert [t.region_id for t in targets] == ids[1:]
    assert all(round(t.support, 6) == 0.285 and round(t.weight, 6) == 0.9 for t in targets)


def test_review_r01_the_weight_follows_the_best_path_not_the_path_taken() -> None:
    """A—X 0.3 direct, A—B—X 0.8 × 0.8 = 0.64; a rumor sitting at X spreads to Y over
    X—Y 0.5 with weight best[X] × 0.5 = 0.32, however it reached X."""
    world = build_snapshot(
        ["a", "b", "x", "y"],
        [
            edge("a", "x", weight=0.3),
            edge("a", "b", weight=0.8),
            edge("b", "x", weight=0.8),
            edge("x", "y", weight=0.5),
        ],
    )
    at_x = deed_rumor("x", support=0.4)
    (to_y,) = plan_spread(world, at_x, origin_region_id="a", reached={"a", "x", "b"}, tuning=TUNING)
    assert to_y.region_id == "y" and round(to_y.weight, 6) == 0.32


def test_a_hop_that_would_die_next_turn_is_not_planned() -> None:
    world = build_snapshot(["a", "b"], [edge("a", "b", weight=0.9)])
    weak = deed_rumor("a", support=0.1)  # 0.1 × 0.95 = 0.095 < floor 0.10
    assert plan_spread(world, weak, origin_region_id="a", reached={"a"}, tuning=TUNING) == []


# --- TP-U6-8: the turn's region quota ---------------------------------------------- #
@given(
    active=st.dictionaries(st.sampled_from(list("abc")), st.integers(0, 25)),
    adds=st.lists(st.sampled_from(list("abc")), max_size=40),
    cap=st.integers(0, 20),
)
def test_tp_u6_8_seeds_spread_and_drafts_together_stay_under_the_cap(active, adds, cap):
    quota = RegionQuota(active, cap)
    total = Counter(active)
    for region in adds:  # seeds, spreads and drafts all go through the same quota
        if quota.full(region):
            continue
        quota.add(region)
        total[region] += 1
    for region in set(adds):
        assert total[region] <= max(cap, active.get(region, 0))
        assert quota.reserved(region) == total[region] - active.get(region, 0)


# --- FD review R-15: the birth-turn exemption is per rumor ------------------------ #
def test_review_r15_only_the_newborn_deed_rumor_skips_decay() -> None:
    old = deed_rumor("a", support=0.30, rumor_id="old")
    newborn = deed_rumor("a", support=0.30, rumor_id="new")
    canon = _canonical("a").model_copy(update={"support": 0.30})
    decay_support([old, newborn, canon], set(), decay=0.05, exempt_ids={"new"})
    assert (round(old.support, 6), round(newborn.support, 6), round(canon.support, 6)) == (
        0.25,
        0.30,
        0.25,
    )
