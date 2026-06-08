"""Connection weight computation (U3, FD3-Q3/Q4=A).

Deterministic: base weight per connection kind, multiplied by terrain modifiers
derived from a heuristic table. Wiki priors supply rationale (recorded
separately), not the numeric value — so weights are reproducible/testable.
"""

from __future__ import annotations

from ..models import ConnectionKind

BASE_WEIGHT: dict[str, float] = {
    ConnectionKind.ADJACENT.value: 0.8,
    ConnectionKind.ROUTE.value: 0.6,
    ConnectionKind.RIVER.value: 0.5,
    ConnectionKind.BLOCKED.value: 0.2,
}
DEFAULT_BASE = 0.5

# terrain feature kind -> multiplicative modifier on connection weight
TERRAIN_MODIFIER: dict[str, float] = {
    "mountain": 0.4,
    "range": 0.4,
    "mountains": 0.4,
    "desert": 0.5,
    "river": 0.8,
    "sea": 0.3,
    "ocean": 0.3,
    "road": 1.2,
    "route": 1.2,
    "bridge": 1.2,
}
DEFAULT_MODIFIER = 1.0


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def base_weight(kind: str) -> float:
    return BASE_WEIGHT.get(str(kind), DEFAULT_BASE)


def terrain_modifier(terrain_kind: str) -> float:
    return TERRAIN_MODIFIER.get(str(terrain_kind).strip().lower(), DEFAULT_MODIFIER)


def compute_weight(kind: str, terrain_kinds: list[str] | None = None) -> float:
    """weight = clamp(base[kind] * product(terrain modifiers), 0, 1)."""
    weight = base_weight(kind)
    for tk in terrain_kinds or []:
        weight *= terrain_modifier(tk)
    return clamp(weight)
