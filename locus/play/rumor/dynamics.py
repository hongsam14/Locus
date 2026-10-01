"""Rumor lifecycle pure logic (Phase 2 hardening / U-H1, FR-H1..H4).

support(공신력) is the "aliveness" lever: unreinforced rumors decay each turn and
are pruned below a floor, only sufficiently-supported rumors are eligible to seed
new distortions, and high-support rumor density feeds back into a region's
distortion. All functions here are pure and deterministic — no LLM, no DB, no
side effects (NFR-H1, PBT target). Event support *reinforcement* stays in
``dynamics.evolve_support`` (BR-H1-20); this module owns *decay*, prune, source
eligibility, and region feedback.

Parameters live in ``PlayTuning`` (shared dataclass, assembled from Settings,
FR-H4 / FR-A7) and are passed as function arguments so the maths stays deterministic.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from locus.play.models import DEFAULT_DISTORTION_DEGREE, SessionRumor
from locus.shared.config.tuning import PlayTuning
from locus.shared.models.util import clamp01

DEFAULT_RUMOR_DYNAMICS = PlayTuning()


def decay_support(
    rumors: list[SessionRumor],
    reinforced_region_ids: set[str],
    *,
    decay: float = DEFAULT_RUMOR_DYNAMICS.support_decay,
    exempt_ids: frozenset[str] | set[str] = frozenset(),
) -> list[SessionRumor]:
    """Decay support of unreinforced, non-promoted rumors in place (BR-H1-1/2/3).

    Runs every turn (incl. empty turns, FD-H Q1=A). A rumor is exempt when it is
    promoted (합의된 사실 보호, Q6=A), sits in a region reinforced this turn
    (event-influenced ∪ feedback regions, Q2=A), or is listed in ``exempt_ids`` — U6
    passes the deed rumors born this turn, so a far hop is not pruned at birth while
    its neighbours still decay (rumor-level, FD review R-15). Returns the same
    (mutated) list for convenient persistence by the caller. Callers pass ACTIVE
    rumors only (BR-H1-11).
    """
    for r in rumors:
        if r.promoted or r.region_id in reinforced_region_ids or r.id in exempt_ids:
            continue
        r.support = clamp01(r.support - decay)
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

    U7 (BR-U7-1, FD-U7 Q4=A): promoted rumors are the region's accepted facts, not
    rumors, so they count neither as strong nor in the total. One promoted rumor no
    longer keeps a region's feedback — and so its distortion — going for ever.
    """
    totals: dict[str, int] = {}
    strong: dict[str, int] = {}
    for r in rumors:
        if r.promoted:
            continue
        totals[r.region_id] = totals.get(r.region_id, 0) + 1
        if r.support >= high_support_threshold:
            strong[r.region_id] = strong.get(r.region_id, 0) + 1
    out: dict[str, float] = {}
    for region_id, n_strong in strong.items():
        if n_strong <= 0:
            continue
        out[region_id] = weight * (n_strong / totals[region_id])
    return out


# --- U7 feedback share: cap and restore (FD-U7 Q2=A, BR-U7-2/3) ----------------------- #
@dataclass(frozen=True)
class FeedbackState:
    """One region before this turn's feedback step."""

    degree: float  # current distortion
    share: float  # the part of ``degree`` feedback put there


@dataclass(frozen=True)
class FeedbackStep:
    """One region after the step."""

    degree: float
    share: float
    raised: float  # what feedback added this turn (after the cap and the clamp), >= 0
    restored: float  # what was given back this turn, >= 0


def step_feedback(
    states: Mapping[str, FeedbackState],
    deltas: Mapping[str, float],
    *,
    cap: float,
    restore: float,
) -> dict[str, FeedbackStep]:
    """One turn of feedback for every region that has a delta or a share (BLM §1.3).

    A region with a delta is raised by ``min(delta, cap - share)``; only the increase
    that survives the [0, 1] clamp joins its share. A region with no delta and a share
    gives ``min(share, restore)`` back: the degree falls (never below 0) and the share
    falls by the full amount, so it always reaches 0. Other regions are left out. Pure.
    """
    out: dict[str, FeedbackStep] = {}
    for rid in sorted(set(deltas) | {r for r, s in states.items() if s.share > 0}):
        state = states.get(rid, FeedbackState(degree=DEFAULT_DISTORTION_DEGREE, share=0.0))
        delta = deltas.get(rid, 0.0)
        if delta > 0:
            add = min(delta, max(0.0, cap - state.share))
            degree = clamp01(state.degree + add)
            raised = max(0.0, degree - state.degree)
            out[rid] = FeedbackStep(
                degree=degree, share=min(1.0, state.share + raised), raised=raised, restored=0.0
            )
        elif state.share > 0:
            back = min(state.share, restore)
            degree = clamp01(state.degree - back)
            out[rid] = FeedbackStep(
                degree=degree,
                share=max(0.0, state.share - back),
                raised=0.0,
                restored=max(0.0, state.degree - degree),
            )
    return out
