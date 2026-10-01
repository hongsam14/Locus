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
  The source is the **root** of the rumor's chain: a later link distorts the previous
  link, not the knowledge, so hiding only first links let an NPC hold the original and
  its second-link distortion together (code review U5 #1). ``lineage`` carries the
  region's rumors that are not in the pick (unpicked, pruned) so the walk can climb.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping, Sequence

from locus.play.models import DeedMemory, Message, NpcContext, ScopeLimits, SessionRumor
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


def root_source(rumor: SessionRumor, lineage: Mapping[str, SessionRumor]) -> str | None:
    """The canonical knowledge id ``rumor``'s chain started from, or ``None`` when the
    chain does not end in knowledge (a missing parent — e.g. deleted by a regenerate —
    or a non-knowledge origin). Cycles stop the walk."""
    seen: set[str] = set()
    current = rumor
    while current.distorted_from_kind == "rumor":
        if current.id in seen:
            return None
        seen.add(current.id)
        parent = lineage.get(current.distorted_from_id)
        if parent is None:
            return None
        current = parent
    return current.distorted_from_id if current.distorted_from_kind == "knowledge" else None


def shadowed_sources(
    rumors: Iterable[SessionRumor], lineage: Iterable[SessionRumor] = ()
) -> set[str]:
    """Canonical knowledge ids at the root of the given rumors' chains."""
    picked = list(rumors)
    by_id = {r.id: r for r in lineage}
    by_id.update({r.id: r for r in picked})
    roots = (root_source(r, by_id) for r in picked)
    return {root for root in roots if root is not None}


def pick_facts(
    facts: Sequence[KnowledgeView], limit: int, *, hidden: Collection[str] = frozenset()
) -> list[KnowledgeView]:
    """Known-scope facts not hidden, direct → inherited → global, then by confidence."""
    visible = [k for k in facts if is_known_scope(k) and k.knowledge_id not in hidden]
    return sorted(visible, key=_fact_key)[:limit] if limit else []


def pick_rumors(rumors: Sequence[SessionRumor], limit: int) -> list[SessionRumor]:
    """Promoted first, then by support (BR-U5-9). A rumor with no words is never
    picked: it would hide its source and leave the NPC with nothing (review U5 #14)."""
    spoken = [r for r in rumors if r.statement.strip()]
    return sorted(spoken, key=_rumor_key)[:limit] if limit else []


def build_context(
    *,
    npc: NPC,
    facts: Sequence[KnowledgeView],
    rumors: Sequence[SessionRumor],
    recent: Sequence[Message],
    limits: ScopeLimits,
    lineage: Sequence[SessionRumor] = (),
    deeds: Sequence[DeedMemory] = (),
) -> NpcContext:
    """``deeds`` (U6, BR-U6-30) are already this NPC's own memories, bounded by
    ``npc_max_deeds`` in ``DeedService.memories``; they are carried as given."""
    picked_rumors = pick_rumors(rumors, limits.rumors)
    hidden = shadowed_sources(picked_rumors, [*rumors, *lineage])
    picked_facts = pick_facts(facts, limits.facts, hidden=hidden)
    # `recent[-0:]` would return everything: a zero limit means "none".
    picked_recent = list(recent[-limits.recent_messages :]) if limits.recent_messages else []
    return NpcContext(
        npc=npc,
        facts=picked_facts,
        rumors=picked_rumors,
        recent=picked_recent,
        deeds=list(deeds),
        allowed_ids={k.knowledge_id for k in picked_facts}
        | {r.id for r in picked_rumors}
        | {d.deed_id for d in deeds},
    )
