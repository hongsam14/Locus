"""Connection weight computation (U3, FD3-Q3/Q4=A).

Deterministic: base weight per connection kind, multiplied by terrain modifiers
derived from a heuristic table. Wiki priors supply rationale (recorded
separately), not the numeric value — so weights are reproducible/testable.
"""

from __future__ import annotations

from locus.shared.config.tuning import DEFAULT_BASE_WEIGHTS, WorldTuning
from locus.shared.models import ConnectionKind
from locus.shared.models.util import clamp01

# The tables live in ``WorldTuning`` (U7, FR-A7: env-tunable); these are its defaults.
_DEFAULTS = WorldTuning()
DEFAULT_MODIFIER = 1.0


def base_weight(kind: str, tuning: WorldTuning = _DEFAULTS) -> float:
    """The kind's base weight. The kinds are an enum of four and the builder turns an
    unknown kind into ``adjacent`` first (U3 A3-15: no separate default knob)."""
    adjacent = ConnectionKind.ADJACENT.value
    fallback = tuning.base_weights.get(adjacent, DEFAULT_BASE_WEIGHTS[adjacent])
    return tuning.base_weights.get(str(kind), fallback)


def terrain_modifier(terrain_kind: str, tuning: WorldTuning = _DEFAULTS) -> float:
    return tuning.terrain_modifiers.get(str(terrain_kind).strip().lower(), DEFAULT_MODIFIER)


def compute_weight(
    kind: str, terrain_kinds: list[str] | None = None, *, tuning: WorldTuning = _DEFAULTS
) -> float:
    """weight = clamp01(base[kind] * product(terrain modifiers))."""
    weight = base_weight(kind, tuning)
    for tk in terrain_kinds or []:
        weight *= terrain_modifier(tk, tuning)
    return clamp01(weight)
