"""Connection weight computation (U3, FD3-Q3/Q4=A).

Deterministic: base weight per connection kind, multiplied by terrain modifiers
derived from a heuristic table. Wiki priors supply rationale (recorded
separately), not the numeric value — so weights are reproducible/testable.
"""

from __future__ import annotations

from locus.shared.config.tuning import WorldTuning
from locus.shared.models.util import clamp01

# The tables live in ``WorldTuning`` (U7, FR-A7: env-tunable); these are its defaults.
_DEFAULTS = WorldTuning()
BASE_WEIGHT = _DEFAULTS.base_weights
DEFAULT_BASE = _DEFAULTS.default_base
TERRAIN_MODIFIER = _DEFAULTS.terrain_modifiers  # terrain kind -> multiplicative modifier
DEFAULT_MODIFIER = 1.0


def base_weight(kind: str, tuning: WorldTuning = _DEFAULTS) -> float:
    return tuning.base_weights.get(str(kind), tuning.default_base)


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
