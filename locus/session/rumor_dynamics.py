"""Rumor lifecycle pure logic (Phase 2 hardening / U-H1, FR-H1..H4).

support(공신력) is the "aliveness" lever: unreinforced rumors decay each turn and
are pruned below a floor, only sufficiently-supported rumors are eligible to seed
new distortions, and high-support rumor density feeds back into a region's
distortion. All functions here are pure and deterministic — no LLM, no DB, no
side effects (NFR-H1, PBT target). Event support *reinforcement* stays in
``dynamics.evolve_support`` (BR-H1-20); this module owns *decay*, prune, source
eligibility, and region feedback.

Parameters live in ``RumorDynamicsParams`` (assembled from Settings, FR-H4 /
AD-H Q5=B) and are passed as function arguments so the maths stays deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import SessionRumor


@dataclass(frozen=True)
class RumorDynamicsParams:
    """Deterministic tuning knobs for rumor dynamics (FD-H Q3=A defaults).

    Assembled from ``Settings`` (env-overridable); pure functions take the
    individual values as keyword args (default from ``DEFAULT_RUMOR_DYNAMICS``).
    """

    support_decay: float = 0.05  # per-turn support loss for unreinforced rumors (BR-H1-1)
    prune_floor: float = 0.05  # support < floor -> prunable, unless promoted (BR-H1-4)
    min_source_support: float = 0.3  # auto-append source eligibility threshold (BR-H1-7)
    feedback_weight: float = 0.1  # rumor->region distortion delta scale (BR-H1-9)
    high_support_threshold: float = 0.6  # "strong" rumor bar for feedback density (BR-H1-9)
    birth_support: float = 0.2  # initial support of a freshly generated rumor (BR-H1-21, FD-H Q7=A)


DEFAULT_RUMOR_DYNAMICS = RumorDynamicsParams()


def decay_support(
    rumors: list[SessionRumor],
    reinforced_region_ids: set[str],
    *,
    decay: float = DEFAULT_RUMOR_DYNAMICS.support_decay,
) -> list[SessionRumor]:
    """Decay support of unreinforced, non-promoted rumors in place (BR-H1-1/2/3).

    Runs every turn (incl. empty turns, FD-H Q1=A). A rumor is exempt when it is
    promoted (합의된 사실 보호, Q6=A) or sits in a region reinforced this turn
    (event-influenced ∪ feedback regions, Q2=A). Returns the same (mutated) list
    for convenient persistence by the caller. Callers pass ACTIVE rumors only
    (BR-H1-11).
    """
    for r in rumors:
        if r.promoted or r.region_id in reinforced_region_ids:
            continue
        r.support = _clamp(r.support - decay)
    return rumors


def is_prunable(rumor: SessionRumor, *, floor: float = DEFAULT_RUMOR_DYNAMICS.prune_floor) -> bool:
    """Whether a rumor should be pruned: below floor and not promoted (BR-H1-4).

    Promoted rumors are exempt (Q7=A) — they demote via promotion.evaluate but are
    never auto-removed.
    """
    return (not rumor.promoted) and rumor.support < floor


def partition_prunable(
    rumors: list[SessionRumor], *, floor: float = DEFAULT_RUMOR_DYNAMICS.prune_floor
) -> tuple[list[SessionRumor], list[SessionRumor]]:
    """Split ACTIVE rumors into (survivors, prunable) (BR-H1-4/5).

    Pure — the caller soft-flags the prunable ones (``active=False``), never a
    hard delete (Q2=B).
    """
    survivors: list[SessionRumor] = []
    prunable: list[SessionRumor] = []
    for r in rumors:
        (prunable if is_prunable(r, floor=floor) else survivors).append(r)
    return survivors, prunable


def is_eligible_source(
    rumor: SessionRumor, *, min_support: float = DEFAULT_RUMOR_DYNAMICS.min_source_support
) -> bool:
    """Whether a rumor may seed new distortions this turn (BR-H1-7).

    Auto-append (TurnAdvancer) gates existing session-rumor sources on this;
    canonical sources are never gated, and the manual path passes no threshold.
    """
    return rumor.support >= min_support


def region_feedback(
    rumors: list[SessionRumor],
    *,
    weight: float = DEFAULT_RUMOR_DYNAMICS.feedback_weight,
    high_support_threshold: float = DEFAULT_RUMOR_DYNAMICS.high_support_threshold,
) -> dict[str, float]:
    """Per-region distortion delta from high-support rumor density (BR-H1-9, Q4=A).

    ``delta[region] = weight * (strong / total)`` where ``strong`` counts rumors
    with ``support >= high_support_threshold`` in the region. Density (0..1) keeps
    the delta scale stable regardless of how many rumors a region holds. Regions
    with no strong rumors get no entry. Pure; callers pass ACTIVE rumors only.
    """
    totals: dict[str, int] = {}
    strong: dict[str, int] = {}
    for r in rumors:
        totals[r.region_id] = totals.get(r.region_id, 0) + 1
        if r.support >= high_support_threshold:
            strong[r.region_id] = strong.get(r.region_id, 0) + 1
    out: dict[str, float] = {}
    for region_id, n_strong in strong.items():
        if n_strong <= 0:
            continue
        out[region_id] = weight * (n_strong / totals[region_id])
    return out


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
