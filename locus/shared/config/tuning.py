"""Tuning parameters per boundary (FR-A7): plain, frozen dataclasses holding values only.

``shared`` owns the *shape* of every boundary's knobs so that ``Settings`` can
fill them from the environment without importing any boundary (FR-A2). The
boundaries import these types (direction: boundary -> shared).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True)
class KnowledgeTuning:
    """Consensus thresholds (knowledge boundary; env since U7, FR-A7)."""

    propagate_min: float = 0.5  # path weight >= this: knowledge propagates as-is
    hearsay_min: float = 0.15  # hearsay_min <= weight < propagate_min: heard second-hand


# Connection kind -> base weight, terrain feature kind -> multiplicative modifier (U3,
# FD3-Q3/Q4=A). Plain strings: ``shared.config`` holds values only.
DEFAULT_BASE_WEIGHTS: Mapping[str, float] = MappingProxyType(
    {"adjacent": 0.8, "route": 0.6, "river": 0.5, "blocked": 0.2}
)
DEFAULT_TERRAIN_MODIFIERS: Mapping[str, float] = MappingProxyType(
    {
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
)


@dataclass(frozen=True)
class WorldTuning:
    """World-build knobs (world boundary; U7, FR-A7 / US-8.5): the connection weight
    table and the ontology dedup bar."""

    base_weights: Mapping[str, float] = field(default_factory=lambda: DEFAULT_BASE_WEIGHTS)
    default_base: float = 0.5  # a connection kind missing from the table
    terrain_modifiers: Mapping[str, float] = field(
        default_factory=lambda: DEFAULT_TERRAIN_MODIFIERS
    )
    dedup_threshold: float = 0.86  # cosine similarity at or above which two items merge


@dataclass(frozen=True)
class PlayTuning:
    """Deterministic rumor-dynamics knobs (play boundary; FD-H Q3=A defaults).

    Assembled from ``Settings`` (env-overridable, ``RUMOR_*``); pure functions take
    the individual values as keyword args.
    """

    support_decay: float = 0.05  # per-turn support loss for unreinforced rumors (BR-H1-1)
    prune_floor: float = 0.05  # support < floor -> prunable, unless promoted (BR-H1-4)
    min_source_support: float = 0.3  # auto-append source eligibility threshold (BR-H1-7)
    feedback_weight: float = 0.1  # rumor->region distortion delta scale (BR-H1-9)
    # "strong" rumor bar for feedback density (BR-H1-9). Below the promotion bar since
    # U7 (Q4=A): promoted rumors no longer count, so equal bars switched feedback off.
    high_support_threshold: float = 0.45
    birth_support: float = 0.2  # initial support of a freshly generated rumor (BR-H1-21)
    # U4 player mode — movement cost cap and per-turn runaway caps (BR-U4-8/17/18, FD R-15)
    max_move_cost: int = 5  # clamp(ceil(1 / weight), 1, max_move_cost) turns per move
    max_new_rumors_per_region_turn: int = 2  # new rumors a turn may draft per region
    max_llm_calls_per_turn: int = 8  # LlmBudget per turn (one degree step = one call)
    max_active_rumors_per_region: int = 20  # a turn never pushes a region above this
    # U5 NPC dialogue — prompt size (FD-U5 Q3=A without hearsay) and input cap (BR-U5-5)
    npc_max_facts: int = 12
    npc_max_rumors: int = 8
    npc_max_recent_messages: int = 10
    npc_max_message_chars: int = 500
    # U6 deeds & spread (domain-entities §5)
    spread_min_weight: float = 0.15  # reach weight below this: not a spread target
    deed_seed_min_salience: float = 0.5  # a noteworthy appraisal below this seeds nothing
    max_spread_per_region_turn: int = 1  # deed rumors a region may receive per turn
    declare_max_chars: int = 300  # declaration length (400 above)
    npc_max_deeds: int = 5  # deeds in one NPC's dialogue context
    appraisal_max_deeds: int = 8  # deeds judged in one appraisal call (newest first)
    # U7 GM mode & hardening (domain-entities §5.3)
    feedback_cap: float = 0.3  # feedback may raise a region's distortion this much at most
    feedback_restore: float = 0.05  # given back per turn once a region has no strong rumor
    promotion_threshold: float = 0.6  # support >= this: promoted (BR-S2-13)
    event_max_delta: float = 0.3  # magnitude 1.0 -> +0.3 distortion at the target (BR-P2-1)
    event_propagate_min: float = 0.15  # path weight below this: an event does not reach
    event_support_reinforce: float = 0.1  # support gain in event-influenced regions
    max_event_suggestions: int = 5  # n of one suggestion request (400 above)
    suggest_max_regions: int = 30  # regions shown to the event suggester
