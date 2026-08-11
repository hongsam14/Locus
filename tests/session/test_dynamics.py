"""P2 dynamics pure-logic tests (FR-P3/P5) + PBT (Partial, NFR-P4)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from locus.models import ConnectionEdge, ConnectionKind, Provenance, SourceKind
from locus.session import dynamics
from locus.session.models import SessionRumor

_unit = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)


def _edge(src: str, dst: str, weight: float) -> ConnectionEdge:
    return ConnectionEdge(
        world_id="w",
        source_region_id=src,
        target_region_id=dst,
        kind=ConnectionKind.ROUTE,
        weight=weight,
        provenance=Provenance(source=SourceKind.INPUT),
    )


def _rumor(region_id: str, support: float) -> SessionRumor:
    return SessionRumor(
        session_id="s",
        region_id=region_id,
        distorted_from_id="k",
        support=support,
        provenance=Provenance(source=SourceKind.SESSION_RUMOR),
    )


# --- distortion_delta ------------------------------------------------------- #
@given(_unit)
def test_distortion_delta_in_range_and_monotone(m: float) -> None:
    d = dynamics.distortion_delta(m)
    assert 0.0 <= d <= dynamics.MAX_EVENT_DELTA
    assert d == m * dynamics.MAX_EVENT_DELTA


def test_distortion_delta_clamps_input() -> None:
    assert dynamics.distortion_delta(5.0) == dynamics.MAX_EVENT_DELTA
    assert dynamics.distortion_delta(-1.0) == 0.0


# --- propagate_delta -------------------------------------------------------- #
def _conns() -> list[ConnectionEdge]:
    # r0 -- r1 (0.8) -- r2 (0.5); r0 -- r3 (0.1, below threshold via direct)
    return [_edge("r0", "r1", 0.8), _edge("r1", "r2", 0.5), _edge("r0", "r3", 0.1)]


def test_propagate_target_full_neighbors_decay() -> None:
    out = dynamics.propagate_delta("r0", 0.3, _conns())
    assert out["r0"] == 0.3  # target = full
    assert out["r1"] == 0.3 * 0.8  # neighbor decays by path weight
    assert abs(out["r2"] - 0.3 * 0.4) < 1e-9  # 0.8*0.5 = 0.4 path
    assert "r3" not in out  # 0.1 < PROPAGATE_MIN_WEIGHT (0.15) -> dropped


def test_propagate_no_connections() -> None:
    assert dynamics.propagate_delta("r0", 0.3, []) == {"r0": 0.3}


# --- apply / restore symmetry ---------------------------------------------- #
@given(st.floats(0.0, 1.0), st.floats(0.0, 0.3))
def test_apply_then_restore_is_identity_within_clamp(start: float, delta: float) -> None:
    cur = {"r": start}
    applied = dynamics.apply_deltas(cur, {"r": delta})
    restored = dynamics.restore_contributions(applied, {"r": delta})
    # within [0,1] (no clamp saturation) the round-trip returns the start
    if 0.0 <= start + delta <= 1.0:
        assert abs(restored["r"] - start) < 1e-9
    assert 0.0 <= applied["r"] <= 1.0 and 0.0 <= restored["r"] <= 1.0


def test_apply_deltas_clamps_and_defaults_missing() -> None:
    out = dynamics.apply_deltas({}, {"r": 0.9})
    assert out["r"] == 1.0  # 0.3 default + 0.9 -> clamp 1.0
    assert dynamics.apply_deltas({"r": 0.9}, {"r": 0.5})["r"] == 1.0


def test_merge_add_accumulates() -> None:
    out = dynamics.merge_add({"r": 0.2}, {"r": 0.1, "x": 0.3})
    assert abs(out["r"] - 0.3) < 1e-9 and abs(out["x"] - 0.3) < 1e-9


# --- evolve_support --------------------------------------------------------- #
def test_evolve_support_reinforce_and_decay() -> None:
    rumors = [_rumor("rA", 0.5), _rumor("rB", 0.5)]
    dynamics.evolve_support(rumors, {"rA"})
    by_region = {r.region_id: r.support for r in rumors}
    assert abs(by_region["rA"] - 0.6) < 1e-9  # +0.1 reinforce
    assert abs(by_region["rB"] - 0.45) < 1e-9  # -0.05 decay


@given(_unit)
def test_evolve_support_stays_in_range(s: float) -> None:
    r = _rumor("rA", s)
    dynamics.evolve_support([r], {"rA"})
    assert 0.0 <= r.support <= 1.0
    r2 = _rumor("rB", s)
    dynamics.evolve_support([r2], set())
    assert 0.0 <= r2.support <= 1.0
