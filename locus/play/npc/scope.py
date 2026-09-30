"""What an NPC may know — the pure scope function (U5; FR-F4, BR-U5-7..11, PBT-03).

``build_context`` receives the region's static knowledge (direct + inherited +
global), the region's active session rumors and the recent conversation, and
returns the bounded, ordered context one answer may draw on. No I/O: the same
inputs always give the same context (ids break every tie).

Two rules make the unit's core experience hold:

* **No hearsay.** Hearsay is another region's canonical knowledge that reached this
  one over a weak path; letting an NPC recite it would let the undistorted original
  bypass the rumors (US-6.1, US-4.3; design deviation 1). Only direct, inherited and
  global items are accepted, even if a caller passes more.
* **A rumor hides its source.** Rumors are drafted from the region's own knowledge,
  so the original would otherwise sit next to its distortion. The rumors are picked
  first and only the *selected* rumors hide their sources — a rumor cut by the limit
  must not make the NPC forget the event altogether (BR-U5-11, plan review R-12).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from locus.play.models import Message, NpcContext, ScopeLimits, SessionRumor
from locus.shared.models import NPC, KnowledgeView

# The only scopes an NPC's own knowledge may come from (BR-U5-7).
KNOWN_SCOPES = ("direct", "inherited", "global")
_SCOPE_RANK = {scope: rank for rank, scope in enumerate(KNOWN_SCOPES)}


def _fact_key(k: KnowledgeView) -> tuple[int, float, str]:
    return (_SCOPE_RANK.get(str(k.scope_type), len(KNOWN_SCOPES)), -k.confidence, k.knowledge_id)


def _rumor_key(r: SessionRumor) -> tuple[int, float, float, str]:
    return (0 if r.promoted else 1, -r.support, -r.distortion_degree, r.id)


def is_known_scope(k: KnowledgeView) -> bool:
    """Direct, inherited or global — never propagated, never hearsay."""
    return str(k.scope_type) in KNOWN_SCOPES and not k.is_hearsay


def shadowed_sources(rumors: Iterable[SessionRumor]) -> set[str]:
    """Canonical knowledge ids the given rumors were drafted from."""
    return {r.distorted_from_id for r in rumors if r.distorted_from_kind == "knowledge"}


def pick_rumors(rumors: Sequence[SessionRumor], limit: int) -> list[SessionRumor]:
    """Promoted first, then by support (BR-U5-9)."""
    return sorted(rumors, key=_rumor_key)[:limit] if limit else []


def build_context(
    *,
    npc: NPC,
    facts: Sequence[KnowledgeView],
    rumors: Sequence[SessionRumor],
    recent: Sequence[Message],
    limits: ScopeLimits,
) -> NpcContext:
    picked_rumors = pick_rumors(rumors, limits.rumors)
    hidden = shadowed_sources(picked_rumors)
    visible = [k for k in facts if is_known_scope(k) and k.knowledge_id not in hidden]
    picked_facts = sorted(visible, key=_fact_key)[: limits.facts] if limits.facts else []
    # `recent[-0:]` would return everything: a zero limit means "none".
    picked_recent = list(recent[-limits.recent_messages :]) if limits.recent_messages else []
    return NpcContext(
        npc=npc,
        facts=picked_facts,
        rumors=picked_rumors,
        recent=picked_recent,
        allowed_ids={k.knowledge_id for k in picked_facts} | {r.id for r in picked_rumors},
    )
