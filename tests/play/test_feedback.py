"""U7 feedback share — cap and restore (FD-U7 Q2=A, Q4=A; BR-U7-1..5, TP-U7-1..4)."""

from __future__ import annotations

import math

from hypothesis import given
from hypothesis import strategies as st

from locus.play.models import SessionRumor
from locus.play.rumor.dynamics import FeedbackState, region_feedback, step_feedback
from locus.shared.models import Provenance, SourceKind
from tests.play.strategies import feedback_inputs

EPS = 1e-9


def _rumor(region: str, support: float, *, promoted: bool = False) -> SessionRumor:
    return SessionRumor(
        session_id="s",
        region_id=region,
        distorted_from_id="k",
        support=support,
        promoted=promoted,
        provenance=Provenance(source=SourceKind.SIMULATION),
    )


@given(feedback_inputs())
def test_tp_u7_1_one_step_stays_in_range_and_books_what_it_raised(inputs) -> None:
    states, deltas, cap, restore = inputs
    out = step_feedback(states, deltas, cap=cap, restore=restore)
    for rid, step in out.items():
        before = states.get(rid, FeedbackState(degree=0.3, share=0.0))
        assert 0.0 <= step.degree <= 1.0 and 0.0 <= step.share <= cap + EPS
        assert step.raised >= 0.0 and step.restored >= 0.0
        if deltas.get(rid, 0.0) > 0:
            assert abs((step.share - before.share) - step.raised) < EPS
            assert abs((step.degree - before.degree) - step.raised) < EPS
        else:
            assert step.raised == 0.0 and step.degree <= before.degree
    assert set(out) == set(deltas) | {r for r, s in states.items() if s.share > 0}


@given(feedback_inputs())
def test_tp_u7_2_without_strong_rumors_the_share_drains_in_bounded_turns(inputs) -> None:
    states, _deltas, cap, restore = inputs
    for rid, state in states.items():
        cur = state
        bound = math.ceil(state.share / restore) + 1  # one turn of float slack (FD R-09)
        for _ in range(bound):
            step = step_feedback({rid: cur}, {}, cap=cap, restore=restore).get(rid)
            if step is None:
                break
            assert step.share <= cur.share and step.degree <= cur.degree
            cur = FeedbackState(degree=step.degree, share=step.share)
        assert cur.share == 0.0


@given(feedback_inputs(), st.integers(min_value=1, max_value=40))
def test_tp_u7_3_feedback_alone_never_raises_a_region_past_the_cap(inputs, turns) -> None:
    states, deltas, cap, restore = inputs
    for rid in deltas:
        start = states.get(rid, FeedbackState(degree=0.3, share=0.0))
        cur = start
        for _ in range(turns):
            step = step_feedback({rid: cur}, {rid: deltas[rid]}, cap=cap, restore=restore)[rid]
            cur = FeedbackState(degree=step.degree, share=step.share)
        assert cur.degree - start.degree <= (cap - start.share) + EPS


@given(
    st.lists(st.tuples(st.sampled_from(["a", "b"]), st.floats(0, 1, allow_nan=False)), max_size=8),
    st.lists(st.tuples(st.sampled_from(["a", "b"]), st.floats(0, 1, allow_nan=False)), max_size=4),
)
def test_tp_u7_4_promoted_rumors_never_change_the_feedback(plain, promoted) -> None:
    base = [_rumor(r, s) for r, s in plain]
    more = base + [_rumor(r, s, promoted=True) for r, s in promoted]
    kwargs = {"weight": 0.1, "high_support_threshold": 0.45}
    assert region_feedback(base, **kwargs) == region_feedback(more, **kwargs)


def test_ex2_the_feedback_rises_then_gives_itself_back() -> None:
    """EX-2 / BLM §1.5: an input sequence from share 0 (Step 1.3)."""
    state = FeedbackState(degree=0.3, share=0.0)
    seen = []
    for delta in (0.075, 0.025, 0.0, 0.0):
        deltas = {"x": delta} if delta else {}
        step = step_feedback({"x": state}, deltas, cap=0.3, restore=0.05)["x"]
        state = FeedbackState(degree=step.degree, share=step.share)
        seen.append((round(step.degree, 6), round(step.share, 6)))
    assert seen == [(0.375, 0.075), (0.4, 0.1), (0.35, 0.05), (0.3, 0.0)]


def test_ex3_a_share_at_the_cap_raises_nothing_more() -> None:
    near = FeedbackState(degree=0.58, share=0.28)
    step = step_feedback({"x": near}, {"x": 0.075}, cap=0.3, restore=0.05)["x"]
    assert (round(step.raised, 6), round(step.share, 6)) == (0.02, 0.3)
    full = FeedbackState(degree=step.degree, share=step.share)
    again = step_feedback({"x": full}, {"x": 0.1}, cap=0.3, restore=0.05)["x"]
    assert again.raised == 0.0 and again.degree == full.degree


def test_br_u7_1_only_unpromoted_rumors_at_the_bar_are_strong() -> None:
    rumors = [
        _rumor("a", 0.7, promoted=True),
        _rumor("a", 0.5),
        _rumor("a", 0.3),
        _rumor("b", 0.9, promoted=True),
    ]
    out = region_feedback(rumors, weight=0.1, high_support_threshold=0.45)
    assert out == {"a": 0.1 * 1 / 2}  # b: promoted only -> no feedback


# --- the turn engine (Step 5.5): EX-1, the share restored over turns ------------------- #
from locus.play import InMemoryPlayRepository  # noqa: E402
from locus.play.models import TimelineKind  # noqa: E402
from locus.play.rumor.generator import RumorDraft, RumorGenerator  # noqa: E402
from tests.play.helpers import compose_play  # noqa: E402
from tests.play.strategies import build_snapshot, edge  # noqa: E402
from tests.shared.snapshots import StaticSnapshots  # noqa: E402


class _NoLLM:
    def structured(self, prompt, schema, *, system=None):  # pragma: no cover
        return RumorDraft(statement="unused")

    def complete(self, prompt, *, system=None):  # pragma: no cover
        return ""


def _engine():
    repo = InMemoryPlayRepository()
    world = build_snapshot(["a", "b"], [edge("a", "b", weight=0.6)])
    gm = compose_play(repo, RumorGenerator(_NoLLM()), StaticSnapshots(world))
    session = repo.create_session("w")
    repo.set_region_distortion(session.id, "a", 0.3)
    return repo, gm, session


def _put(repo, session, supports, *, promoted=()):
    rumors = [_rumor("a", s).model_copy(update={"session_id": session.id}) for s in supports]
    rumors += [
        _rumor("a", s, promoted=True).model_copy(update={"session_id": session.id})
        for s in promoted
    ]
    repo.upsert_rumors(rumors)
    return rumors


def test_ex1_one_promoted_rumor_no_longer_stops_the_regions_decay() -> None:
    """US-8.2 first: the event is over; a promoted rumor stays, the others fade."""
    repo, gm, session = _engine()
    _put(repo, session, [0.4, 0.4, 0.4], promoted=[0.7])
    result = gm.turns.advance(session.id).turns[-1]
    supports = sorted(round(r.support, 6) for r in repo.list_rumors(session.id, "a"))
    assert supports == [0.35, 0.35, 0.35, 0.7] and result.feedback_regions == []
    for _ in range(7):
        gm.turns.advance(session.id)
    left = repo.list_rumors(session.id, "a")
    assert [r.promoted for r in left] == [True]  # the rest were pruned


def test_br_u7_2_3_the_feedback_share_comes_back_once_the_rumors_fade() -> None:
    """US-8.2 second: strong rumors raise the region, decay (no exemption), and the share
    is given back turn by turn until the region is where it started."""
    repo, gm, session = _engine()
    _put(repo, session, [0.5, 0.5, 0.5, 0.3])
    seen = []
    for _ in range(5):
        gm.turns.advance(session.id)
        row = next(r for r in repo.list_region_distortions(session.id) if r.region_id == "a")
        seen.append((round(row.distortion_degree, 6), round(row.feedback_share, 6)))
    assert seen == [(0.375, 0.075), (0.45, 0.15), (0.4, 0.1), (0.35, 0.05), (0.3, 0.0)]
    restored = [
        e.payload["feedback_restored_regions"]
        for e in repo.list_timeline(session.id)
        if e.kind == TimelineKind.ADVANCE_TURN.value
    ]
    assert restored == [[], [], ["a"], ["a"], ["a"]]


def test_br_u7_5_a_gm_set_is_the_new_base() -> None:
    repo, gm, session = _engine()
    _put(repo, session, [0.5, 0.5, 0.5, 0.3])
    gm.turns.advance(session.id)
    gm.distortions.set_region_distortion(session.id, "a", 0.5)
    row = next(r for r in repo.list_region_distortions(session.id) if r.region_id == "a")
    assert (row.distortion_degree, row.feedback_share) == (0.5, 0.0)
