"""Tuning parameters per boundary (FR-A7): plain, frozen dataclasses holding values only.

``shared`` owns the *shape* of every boundary's knobs so that ``Settings`` can
fill them from the environment without importing any boundary (FR-A2). The
boundaries import these types (direction: boundary -> shared).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeTuning:
    """Consensus thresholds (knowledge boundary)."""

    propagate_min: float = 0.5  # path weight >= this: knowledge propagates as-is
    hearsay_min: float = 0.15  # hearsay_min <= weight < propagate_min: heard second-hand


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
    high_support_threshold: float = 0.6  # "strong" rumor bar for feedback density (BR-H1-9)
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
