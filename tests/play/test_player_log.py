"""U7 player log (FR-C6, Q3=A; BR-U7-12..15, TP-U7-6, EX-10)."""

from __future__ import annotations

from hypothesis import given

from locus.play.models import TimelineEntry, TimelineKind
from locus.play.player.log import HIDDEN_KINDS, OWN_KINDS, REGION_KINDS, player_log
from tests.play.strategies import player_timelines

K = TimelineKind


def _e(kind: TimelineKind, turn: int = 0, **payload) -> TimelineEntry:
    return TimelineEntry(session_id="s", turn=turn, kind=kind, summary=kind.value, payload=payload)


def test_tp_u7_6_the_three_groups_split_every_kind_once() -> None:
    every = {k.value for k in TimelineKind}
    assert OWN_KINDS | REGION_KINDS | HIDDEN_KINDS == every
    assert not (OWN_KINDS & REGION_KINDS or OWN_KINDS & HIDDEN_KINDS or REGION_KINDS & HIDDEN_KINDS)


@given(player_timelines())
def test_tp_u7_6_the_log_is_an_ordered_subset_placed_where_the_player_was(entries) -> None:
    out = player_log(entries)
    ids = [e.id for e in entries]
    positions = [ids.index(e.id) for e in out]
    assert positions == sorted(positions)  # a subsequence, order kept
    here = None
    kept = {e.id for e in out}
    for e in entries:
        if e.kind == K.SESSION_STARTED.value:
            here = e.payload.get("region_id")
        elif e.kind == K.PLAYER_MOVED.value:
            here = e.payload.get("to_region_id")
        elif e.kind == K.TURN_RUN_FAILED.value and e.payload.get("restored_region_id"):
            here = e.payload["restored_region_id"]
        if e.id in kept and e.kind in REGION_KINDS:
            assert e.payload.get("region_id") == here
        if e.kind in OWN_KINDS:
            assert e.id in kept
        if e.kind in HIDDEN_KINDS:
            assert e.id not in kept


def test_ex10_my_doings_and_what_happened_where_i_was() -> None:
    entries = [
        _e(K.SESSION_STARTED, 0, region_id="a", region_name="A"),
        _e(K.EVENT_APPLIED, 0, event_id="e1", region_id="a"),
        _e(K.ADVANCE_TURN, 1),
        _e(K.EVENT_APPLIED, 1, event_id="e1", region_id="a"),  # same stay: shown once
        _e(K.PRUNE, 1, rumor_id="r9", region_id="c"),  # another region
        _e(K.PLAYER_MOVED, 1, from_region_id="a", to_region_id="b", region_id="b"),
        _e(K.EVENT_APPLIED, 1, event_id="e1", region_id="a"),  # left a
        _e(K.SET_DISTORTION, 2, region_id="b", degree=0.9),  # the GM's hand
        _e(K.PROMOTE, 2, rumor_id="r1", region_id="b"),
        _e(K.DEED_APPRAISED, 2, deed_id="d1", region_id="b"),  # an NPC's private judgement
        _e(K.PROMOTE, 2, rumor_id="r0"),  # written before U7: no region
    ]
    kinds = [(e.kind, e.payload.get("region_id")) for e in player_log(entries)]
    assert kinds == [
        ("session_started", "a"),
        ("event_applied", "a"),
        ("player_moved", "b"),
        ("promote", "b"),
    ]


def test_br_u7_14_a_persistent_event_is_shown_again_after_coming_back() -> None:
    entries = [
        _e(K.SESSION_STARTED, 0, region_id="a"),
        _e(K.EVENT_APPLIED, 0, event_id="e1", region_id="a"),
        _e(K.PLAYER_MOVED, 0, to_region_id="b"),
        _e(K.PLAYER_MOVED, 1, to_region_id="a"),
        _e(K.EVENT_APPLIED, 2, event_id="e1", region_id="a"),
    ]
    assert [e.kind for e in player_log(entries)].count("event_applied") == 2


def test_a_gm_session_start_has_no_region_and_hides_region_lines() -> None:
    entries = [_e(K.SESSION_STARTED, 0, player=None), _e(K.PROMOTE, 1, region_id="a")]
    assert [e.kind for e in player_log(entries)] == ["session_started"]


def test_review_u7_5_a_failed_move_puts_the_log_back_where_the_player_stands() -> None:
    entries = [
        _e(K.SESSION_STARTED, 0, region_id="a"),
        _e(K.PLAYER_MOVED, 0, to_region_id="b", region_id="b"),
        _e(K.TURN_RUN_FAILED, 0, run_id="r", restored_region_id="a"),
        _e(K.EVENT_APPLIED, 0, event_id="ea", region_id="a"),
        _e(K.EVENT_APPLIED, 0, event_id="eb", region_id="b"),
    ]
    shown = [(e.kind, e.payload.get("region_id")) for e in player_log(entries)]
    assert ("event_applied", "a") in shown and ("event_applied", "b") not in shown


def test_review_u7_5_the_engine_records_where_the_player_was_put_back() -> None:
    import pytest

    from locus.play import InMemoryPlayRepository
    from locus.play.models import MoveAction, PlayerCreate
    from locus.play.rumor.generator import RumorDraft, RumorGenerator
    from tests.play.helpers import compose_play
    from tests.play.strategies import build_snapshot, edge
    from tests.shared.snapshots import StaticSnapshots

    class _LLM:
        def structured(self, prompt, schema, *, system=None):  # pragma: no cover
            return RumorDraft(statement="x")

        def complete(self, prompt, *, system=None):  # pragma: no cover
            return ""

    repo = InMemoryPlayRepository()
    world = build_snapshot(["a", "b"], [edge("a", "b", weight=0.6), edge("b", "a", weight=0.6)])
    gm = compose_play(repo, RumorGenerator(_LLM()), StaticSnapshots(world))
    session, _p = gm.sessions.start("w", PlayerCreate(name="Ari", start_region_id="a"))

    def boom(*args, **kwargs):
        raise RuntimeError("turn failed")

    gm.turns._one_turn = boom  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        gm.turns.advance(session.id, MoveAction(to_region_id="b"))
    failed = [e for e in repo.list_timeline(session.id) if e.kind == "turn_run_failed"]
    assert failed[-1].payload["restored_region_id"] == "a"
    assert [e.kind for e in gm.play.log(session.id)][-1] == "turn_run_failed"
