"""The player's view of the session timeline (U7, FR-C6, BR-U7-12..15).

The GM timeline shows everything. The player's log shows what the player did and what
happened in the region the player was in at that moment — never the GM's hand (rumor
generation, distortion, event suggestions), the NPCs' private judgements, or other
regions. "Where the player was" is read off the timeline itself: the latest
``session_started`` or ``player_moved`` line before an entry decides it (BR-U7-13).
Pure: the same entries always give the same log.
"""

from __future__ import annotations

from collections.abc import Sequence

from locus.play.models import TimelineEntry, TimelineKind

K = TimelineKind

# The player's own doings — always shown.
OWN_KINDS: frozenset[str] = frozenset(
    k.value
    for k in (
        K.SESSION_STARTED,
        K.SESSION_CLOSED,
        K.PLAYER_MOVED,
        K.PLAYER_WAITED,
        K.NPC_TALKED,
        K.ACTION_DECLARED,
        K.DEED_RECORDED,
        K.TURN_RUN_FAILED,
    )
)
# What happens to a region — shown only while the player is there.
REGION_KINDS: frozenset[str] = frozenset(
    k.value
    for k in (
        K.EVENT_APPLIED,
        K.EVENT_RESOLVED,
        K.PROMOTE,
        K.DEMOTE,
        K.PRUNE,
        K.DEED_SEEDED,
        K.RUMOR_SPREAD,
    )
)
# The GM's hand, the turn machinery, NPC judgements and voids — never shown.
HIDDEN_KINDS: frozenset[str] = frozenset(
    k.value
    for k in (
        K.GENERATE,
        K.REGENERATE,
        K.ADJUST_SUPPORT,
        K.SET_DISTORTION,
        K.ADVANCE_TURN,
        K.EVENT_CREATED,
        K.EVENT_SUGGESTED,
        K.EVENT_APPROVED,
        K.EVENT_DISCARDED,
        K.DEED_APPRAISED,
        K.DEED_VOIDED,
    )
)


def player_log(entries: Sequence[TimelineEntry]) -> list[TimelineEntry]:
    """The entries the player may see, in their original order (BR-U7-12..15).

    ``entries`` must be in timeline order (``turn``, then ``created_at``). A region entry
    is kept when its ``region_id`` is the player's region at that point; a persistent
    event's ``event_applied`` is kept once per stay (BR-U7-14). Region entries written
    before U7 carry no ``region_id`` and stay hidden (BR-U7-15).
    """
    here: str | None = None
    seen_events: set[str] = set()
    out: list[TimelineEntry] = []
    for e in entries:
        kind = str(e.kind)
        if kind == K.SESSION_STARTED.value:
            here = e.payload.get("region_id")
            seen_events = set()
        elif kind == K.PLAYER_MOVED.value:
            here = e.payload.get("to_region_id") or e.payload.get("region_id")
            seen_events = set()
        if kind in OWN_KINDS:
            out.append(e)
        elif kind in REGION_KINDS and here is not None and e.payload.get("region_id") == here:
            if kind == K.EVENT_APPLIED.value:
                event_id = str(e.payload.get("event_id"))
                if event_id in seen_events:
                    continue
                seen_events.add(event_id)
            out.append(e)
    return out
