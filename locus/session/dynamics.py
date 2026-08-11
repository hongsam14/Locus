"""Dynamic-distortion pure logic (Phase 2 / P2, FR-P3/P5).

All functions here are pure and deterministic — no LLM, no DB, no side effects
(NFR-P4, PBT target). The GameMasterService collects inputs, calls these, then
persists results via the SessionRepository port.

Constants (FD-P2 answers, all A):
- distortion delta = magnitude * MAX_EVENT_DELTA            (Q1)
- topology propagation reuses ``best_path_weights``, neighbours kept when the
  path weight >= PROPAGATE_MIN_WEIGHT                       (Q2)
- support evolves +SUPPORT_REINFORCE for event-influenced regions, else
  -SUPPORT_DECAY                                            (Q4)
"""

from __future__ import annotations

from ..consensus.propagation import best_path_weights
from ..models import ConnectionEdge
from .models import DEFAULT_DISTORTION_DEGREE, SessionRumor

MAX_EVENT_DELTA = 0.3  # FD-P2 Q1: magnitude=1.0 -> +0.3 distortion in one turn
PROPAGATE_MIN_WEIGHT = 0.15  # FD-P2 Q2: matches consensus rumor_min
SUPPORT_REINFORCE = 0.1  # FD-P2 Q4: support gain on event-influenced regions
SUPPORT_DECAY = 0.05  # FD-P2 Q4: support loss elsewhere


def distortion_delta(magnitude: float) -> float:
    """Distortion increase a single event applies at its target (BR-P2-1)."""
    return _clamp(magnitude) * MAX_EVENT_DELTA


def propagate_delta(
    region_id: str,
    base_delta: float,
    connections: list[ConnectionEdge],
    *,
    min_weight: float = PROPAGATE_MIN_WEIGHT,
) -> dict[str, float]:
    """Spread ``base_delta`` from the target over the topology (BR-P2-2).

    Target gets the full delta; each reachable neighbour gets
    ``base_delta * best_path_weight`` when that weight >= ``min_weight``.
    Pure (reuses the consensus max-product reachability).
    """
    weights = best_path_weights(region_id, connections)
    out: dict[str, float] = {region_id: base_delta}
    for rid, w in weights.items():
        if rid == region_id:
            continue
        if w >= min_weight:
            out[rid] = base_delta * w
    return out


def apply_deltas(current: dict[str, float], deltas: dict[str, float]) -> dict[str, float]:
    """Add per-region deltas to current distortion, clamped to [0,1] (BR-P2-3).

    Cumulative: a persistent event re-applying each turn drives the value up via
    repeated calls. Missing regions start from ``DEFAULT_DISTORTION_DEGREE``.
    """
    out = dict(current)
    for rid, d in deltas.items():
        out[rid] = _clamp(out.get(rid, DEFAULT_DISTORTION_DEGREE) + d)
    return out


def restore_contributions(
    current: dict[str, float], contributions: dict[str, float]
) -> dict[str, float]:
    """Symmetrically subtract an event's accumulated contributions (BR-P2-5).

    Used when a persistent event resolves: reverses what it added (target +
    propagated neighbours), clamped to [0,1].
    """
    out = dict(current)
    for rid, d in contributions.items():
        out[rid] = _clamp(out.get(rid, DEFAULT_DISTORTION_DEGREE) - d)
    return out


def evolve_support(
    rumors: list[SessionRumor],
    influenced_region_ids: set[str],
    *,
    reinforce: float = SUPPORT_REINFORCE,
    decay: float = SUPPORT_DECAY,
) -> list[SessionRumor]:
    """Auto-evolve support in place: influenced regions gain, others decay (BR-P2-8).

    Returns the same list (mutated) for convenient persistence by the caller.
    """
    for r in rumors:
        step = reinforce if r.region_id in influenced_region_ids else -decay
        r.support = _clamp(r.support + step)
    return rumors


def merge_add(base: dict[str, float], deltas: dict[str, float]) -> dict[str, float]:
    """Accumulate per-region deltas into an event's contributions map (pure)."""
    out = dict(base)
    for rid, d in deltas.items():
        out[rid] = out.get(rid, 0.0) + d
    return out


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
