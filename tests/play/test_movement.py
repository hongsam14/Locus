"""U4 movement rules — TP-U4-1/2 (PBT-03) + EX-4 / BR-U4-9 (Step 4.6)."""

from __future__ import annotations

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from locus.play.errors import InvalidActionError
from locus.play.models import EndTalkAction, MoveAction, Player, WaitAction
from locus.play.player import movement
from locus.shared.config.tuning import PlayTuning
from locus.shared.models import ConnectionKind
from tests.play.strategies import build_snapshot, connections, edge, npc, topologies, weights

TUNING = PlayTuning()


@given(c=connections())
def test_tp_u4_1_cost_is_within_range_when_passable(c) -> None:
    cost = movement.move_cost(c, TUNING)
    if movement.is_passable(c):
        assert 1 <= cost <= TUNING.max_move_cost
        cap = TUNING.max_move_cost
        expected = cap if c.weight * cap <= 1.0 else max(1, math.ceil(1.0 / c.weight))
        assert cost == expected
    else:
        assert cost == 0


@given(w1=weights.filter(lambda w: w > 0), w2=weights.filter(lambda w: w > 0))
def test_tp_u4_1_cost_is_monotone_in_weight(w1: float, w2: float) -> None:
    lo, hi = sorted((w1, w2))
    assert movement.move_cost(edge("a", "b", weight=lo), TUNING) >= movement.move_cost(
        edge("a", "b", weight=hi), TUNING
    )


@given(c=connections())
def test_tp_u4_2_blocked_or_zero_weight_is_not_passable(c) -> None:
    expected = str(c.kind) != "blocked" and c.weight > 0.0
    assert movement.is_passable(c) is expected
    snap = build_snapshot(["a", "b"], [c])
    opts = movement.move_options(snap, "a", TUNING)
    assert len(opts) == 1 and opts[0].passable is expected
    player = Player(session_id="s", name="Ari", region_id="a")
    if expected:
        assert (
            movement.validate_action(snap, player, MoveAction(to_region_id="b"), TUNING) is not None
        )
    else:
        with pytest.raises(InvalidActionError, match="blocked pass"):
            movement.validate_action(snap, player, MoveAction(to_region_id="b"), TUNING)


@given(snap=topologies())
def test_tp_u4_8_move_options_cover_exactly_the_neighbours(snap) -> None:
    for rid in snap.regions_by_id:
        opts = movement.move_options(snap, rid, TUNING)
        assert {o.region_id for o in opts} == movement.neighbours(snap, rid)
        assert len({o.region_id for o in opts}) == len(opts)  # one option per neighbour
        flags = [o.passable for o in opts]
        assert flags == sorted(flags, reverse=True)  # passable first


def test_ex4_move_to_unconnected_region_is_rejected() -> None:
    snap = build_snapshot(["a", "b", "c"], [edge("a", "b", weight=1.0), edge("b", "a", weight=1.0)])
    player = Player(session_id="s", name="Ari", region_id="a")
    with pytest.raises(InvalidActionError, match="not connected"):
        movement.validate_action(snap, player, MoveAction(to_region_id="c"), TUNING)
    assert movement.validate_action(snap, player, WaitAction(), TUNING) is None


def test_br_u4_9_cheapest_passable_connection_wins() -> None:
    snap = build_snapshot(
        ["a", "b"],
        [
            edge("a", "b", weight=0.2, kind=ConnectionKind.RIVER),  # cost 5
            edge("a", "b", weight=0.0, kind=ConnectionKind.BLOCKED),
            edge("a", "b", weight=1.0, kind=ConnectionKind.ROUTE),  # cost 1
        ],
    )
    opts = movement.move_options(snap, "a", TUNING)
    assert len(opts) == 1 and opts[0].cost_turns == 1 and opts[0].kind == "route"


def test_cost_examples_from_the_design() -> None:
    for w, cost in ((1.0, 1), (0.5, 2), (0.34, 3), (0.2, 5), (0.01, 5)):
        assert movement.move_cost(edge("a", "b", weight=w), TUNING) == cost


def test_end_talk_requires_the_npc_to_be_here() -> None:
    snap = build_snapshot(["a", "b"], [], npcs=[npc("n1", "a"), npc("n2", "b")])
    player = Player(session_id="s", name="Ari", region_id="a")
    assert movement.validate_action(snap, player, EndTalkAction(npc_id="n1"), TUNING) is None
    with pytest.raises(InvalidActionError, match="npc not here"):
        movement.validate_action(snap, player, EndTalkAction(npc_id="n2"), TUNING)


def test_validate_action_raises_lookup_when_player_region_vanished() -> None:
    snap = build_snapshot(["a"], [])
    player = Player(session_id="s", name="Ari", region_id="gone")
    with pytest.raises(LookupError):
        movement.validate_action(snap, player, WaitAction(), TUNING)


def test_action_cost() -> None:
    from locus.play.models import MoveOption

    opt = MoveOption(region_id="b", region_name="B", kind="route", weight=0.5, cost_turns=2)
    assert movement.action_cost(MoveAction(to_region_id="b"), opt) == 2
    assert movement.action_cost(WaitAction(), None) == 1
    assert movement.action_cost(None, None) == 1


@given(st.integers(min_value=1, max_value=9))
def test_max_move_cost_is_honoured(cap: int) -> None:
    assert movement.move_cost(edge("a", "b", weight=0.001), PlayTuning(max_move_cost=cap)) == cap
