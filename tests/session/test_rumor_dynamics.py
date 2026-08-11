"""U-H1 rumor_dynamics pure-logic tests + PBT (NFR-H1/H3, BR-H1-1..9)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from locus.models import Provenance, SourceKind
from locus.session.models import SessionRumor
from locus.session.rumor_dynamics import (
    DEFAULT_RUMOR_DYNAMICS,
    RumorDynamicsParams,
    decay_support,
    is_eligible_source,
    is_prunable,
    partition_prunable,
    region_feedback,
)


def _rumor(
    support: float, *, region_id: str = "r", promoted: bool = False, active: bool = True
) -> SessionRumor:
    return SessionRumor(
        session_id="s",
        region_id=region_id,
        distorted_from_id="k",
        support=support,
        promoted=promoted,
        active=active,
        provenance=Provenance(source=SourceKind.SESSION_RUMOR),
    )


# --- defaults --------------------------------------------------------------- #
def test_default_params_values() -> None:
    p = DEFAULT_RUMOR_DYNAMICS
    assert (p.support_decay, p.prune_floor, p.min_source_support) == (0.05, 0.05, 0.3)
    assert (p.feedback_weight, p.high_support_threshold, p.birth_support) == (0.1, 0.6, 0.2)


# --- decay_support ---------------------------------------------------------- #
def test_decay_reduces_unreinforced_support() -> None:
    r = _rumor(0.4, region_id="r1")
    decay_support([r], set(), decay=0.05)
    assert abs(r.support - 0.35) < 1e-9


def test_decay_exempts_reinforced_region() -> None:
    r = _rumor(0.4, region_id="r1")
    decay_support([r], {"r1"}, decay=0.05)
    assert abs(r.support - 0.4) < 1e-9  # reinforced -> untouched


def test_decay_exempts_promoted() -> None:
    r = _rumor(0.4, region_id="r1", promoted=True)
    decay_support([r], set(), decay=0.05)
    assert abs(r.support - 0.4) < 1e-9  # promoted -> exempt (BR-H1-3)


def test_decay_clamps_at_zero() -> None:
    r = _rumor(0.02, region_id="r1")
    decay_support([r], set(), decay=0.05)
    assert r.support == 0.0


# --- is_prunable / partition ------------------------------------------------ #
def test_prunable_below_floor_not_promoted() -> None:
    assert is_prunable(_rumor(0.04), floor=0.05) is True


def test_not_prunable_at_or_above_floor() -> None:
    assert is_prunable(_rumor(0.05), floor=0.05) is False


def test_promoted_never_prunable() -> None:
    assert is_prunable(_rumor(0.0, promoted=True), floor=0.05) is False  # Q7=A


def test_partition_splits_survivors_and_prunable() -> None:
    keep = _rumor(0.5)
    keep_promoted = _rumor(0.0, promoted=True)  # exempt
    drop = _rumor(0.01)
    survivors, prunable = partition_prunable([keep, keep_promoted, drop], floor=0.05)
    assert {r.id for r in survivors} == {keep.id, keep_promoted.id}
    assert [r.id for r in prunable] == [drop.id]


# --- is_eligible_source ----------------------------------------------------- #
def test_eligible_source_at_threshold() -> None:
    assert is_eligible_source(_rumor(0.3), min_support=0.3) is True
    assert is_eligible_source(_rumor(0.29), min_support=0.3) is False


# --- region_feedback -------------------------------------------------------- #
def test_region_feedback_density() -> None:
    rumors = [
        _rumor(0.7, region_id="r1"),  # strong
        _rumor(0.2, region_id="r1"),  # weak
        _rumor(0.9, region_id="r2"),  # strong (sole)
    ]
    out = region_feedback(rumors, weight=0.1, high_support_threshold=0.6)
    assert abs(out["r1"] - 0.1 * (1 / 2)) < 1e-9
    assert abs(out["r2"] - 0.1 * (1 / 1)) < 1e-9


def test_region_feedback_no_strong_no_entry() -> None:
    out = region_feedback([_rumor(0.3, region_id="r1")], weight=0.1, high_support_threshold=0.6)
    assert out == {}


# --- PBT (Partial) ---------------------------------------------------------- #
@given(
    support=st.floats(min_value=0.0, max_value=1.0),
    decay=st.floats(min_value=0.0, max_value=1.0),
    reinforced=st.booleans(),
    promoted=st.booleans(),
)
def test_pbt_decay_in_range_and_monotone(
    support: float, decay: float, reinforced: bool, promoted: bool
) -> None:
    r = _rumor(support, region_id="r1", promoted=promoted)
    decay_support([r], {"r1"} if reinforced else set(), decay=decay)
    assert 0.0 <= r.support <= 1.0
    if reinforced or promoted:
        assert r.support == support  # exempt
    else:
        assert r.support <= support  # never increases


@given(
    supports=st.lists(st.floats(min_value=0.0, max_value=1.0), min_size=0, max_size=8),
    weight=st.floats(min_value=0.0, max_value=1.0),
    threshold=st.floats(min_value=0.0, max_value=1.0),
)
def test_pbt_feedback_deltas_nonneg_and_bounded(
    supports: list[float], weight: float, threshold: float
) -> None:
    rumors = [_rumor(s, region_id="r1") for s in supports]
    out = region_feedback(rumors, weight=weight, high_support_threshold=threshold)
    for delta in out.values():
        assert 0.0 <= delta <= weight  # density in [0,1] -> delta in [0, weight]


@given(
    support=st.floats(min_value=0.0, max_value=1.0),
    floor=st.floats(min_value=0.0, max_value=1.0),
    promoted=st.booleans(),
)
def test_pbt_prunable_matches_definition(support: float, floor: float, promoted: bool) -> None:
    r = _rumor(support, promoted=promoted)
    assert is_prunable(r, floor=floor) == ((not promoted) and support < floor)


def test_params_is_frozen() -> None:
    p = RumorDynamicsParams()
    try:
        p.support_decay = 0.9  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("RumorDynamicsParams should be frozen")
