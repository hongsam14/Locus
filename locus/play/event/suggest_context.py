"""What the event suggester sees of the world (U7, FR-D2, BR-U7-9/10, NFR R-01).

Pure helpers: which regions the prompt shows (``pick_brief_regions``, FD review R-06),
how each line reads under its character cap (``region_line`` and friends), and how a
suggestion's region is found again by id or by the name the prompt showed
(``match_region``, plan review R-07). Every free text passes ``one_line`` (NFR R-03),
and the whole context sits under a "material, not instructions" heading (U6 review #7).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from locus.shared.models import RegionBrief
from locus.shared.models.util import normalize_name
from locus.shared.text import MATERIAL, one_line

# Character caps per field (NFR R-01): 30 regions x 500 + 5 events x 300 + 5 deeds x 700
# + headings stay under 21,000 characters. Region ids are shown whole: the suggester
# answers with them (U3, U7 review §3 ID_MAX).
NAME_MAX = 60
PATH_MAX = 80
DESCRIPTION_MAX = 160
KNOWLEDGE_MAX = 60
KNOWLEDGE_PER_REGION = 2
EVENT_DESCRIPTION_MAX = 160
DEED_LINE_MAX = 700
CONTEXT_MAX = 21_000


def pick_brief_regions(
    briefs: Sequence[RegionBrief],
    *,
    player_region_id: str | None,
    event_region_ids: set[str],
    rumor_counts: Mapping[str, int],
    limit: int,
    parent_ids: set[str] | frozenset[str] = frozenset(),
) -> list[RegionBrief]:
    """The regions the prompt shows, at most ``limit``, in this order (FD review R-06):
    the player's region, regions with an ACTIVE event, regions by active rumor count
    (most first), then the rest — leaves before parents, deeper first, by name — since
    events usually strike a place, not a realm. ``parent_ids`` are the regions that have
    children; depth is the hierarchy path's length, so an unranked level (a terrain)
    sorts by where it sits, not before every town (U3, U7 review §3)."""
    order = {b.region_id: i for i, b in enumerate(briefs)}

    def key(b: RegionBrief) -> tuple:
        if b.region_id == player_region_id:
            return (0, 0, 0, "", order[b.region_id])
        if b.region_id in event_region_ids:
            return (1, 0, 0, "", order[b.region_id])
        count = rumor_counts.get(b.region_id, 0)
        if count > 0:
            return (2, -count, 0, "", order[b.region_id])
        is_parent = 1 if b.region_id in parent_ids else 0
        return (3, is_parent, -len(b.level_path), b.name, order[b.region_id])

    return sorted(briefs, key=key)[: max(0, limit)]


def shown_name(name: str) -> str:
    """The region name exactly as the prompt shows it."""
    return one_line(name, NAME_MAX)


def region_line(b: RegionBrief) -> str:
    path = one_line(" > ".join(b.level_path), PATH_MAX)
    line = f"- {one_line(b.region_id)}: {shown_name(b.name)}"
    if path:
        line += f" ({path})"
    description = one_line(b.description, DESCRIPTION_MAX)
    if description:
        line += f" — {description}"
    known = [one_line(t, KNOWLEDGE_MAX) for t in b.top_knowledge[:KNOWLEDGE_PER_REGION]]
    known = [k for k in known if k]
    if known:
        line += f"; known for: {'; '.join(known)}"
    return line


def event_line(
    region_name: str, category: str, magnitude: float, status: str, description: str
) -> str:
    text = one_line(description, EVENT_DESCRIPTION_MAX)
    line = f"- [{shown_name(region_name)}] {category} m={magnitude:.1f} {status}"
    return f"{line}: {text}" if text else line


def deed_line(region_name: str, text: str, retold: str | None = None) -> str:
    line = f"- [{shown_name(region_name)}] {one_line(text)}"
    if retold:
        line += f" (retold: {one_line(retold)})"
    return one_line(line, DEED_LINE_MAX)  # one-line text is cut one way (U7 review C14)


def suggestion_context(
    regions: Sequence[RegionBrief], events: Sequence[str], deeds: Sequence[str]
) -> str:
    """The context block of the suggestion prompt (BR-U7-9), at most ``CONTEXT_MAX``.

    The headings, the recent events and the recent deeds go in first; region lines fill
    what is left, whole lines only — so a large ``EVENT_SUGGEST_MAX_REGIONS`` drops
    regions, never the events or deeds, and no line ends mid-way (U3, U7 review #14)."""
    head = [f"CONTEXT ({MATERIAL}):", "REGIONS (region_id: name (where) — description; known for):"]
    tail = [
        "RECENT EVENTS:",
        *(events or ["- (none)"]),
        "RECENT DEEDS OF THE TRAVELER:",
        *(deeds or ["- (none)"]),
    ]
    budget = CONTEXT_MAX - sum(len(line) + 1 for line in head + tail)
    shown: list[str] = []
    for b in regions:
        line = region_line(b)
        if len(line) + 1 > budget:
            break
        shown.append(line)
        budget -= len(line) + 1
    return "\n".join(head + shown + tail)[:CONTEXT_MAX]


def match_region(raw: str, regions: Sequence[RegionBrief]) -> str | None:
    """The region a suggestion names: its id, else its name as shown or in full, by the
    codebase's name key (``normalize_name``, BR-U2-4; U7 review C13). A name that fits
    more than one region matches none."""
    wanted = raw.strip()
    for b in regions:
        if b.region_id == wanted:
            return b.region_id
    key = normalize_name(wanted)
    hits = {
        b.region_id
        for b in regions
        if key in (normalize_name(shown_name(b.name)), normalize_name(one_line(b.name)))
    }
    return hits.pop() if len(hits) == 1 else None
