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
from locus.shared.models.util import rank_of
from locus.shared.text import MATERIAL, one_line

# Character caps per field (NFR R-01): 30 regions x 500 + 5 events x 300 + 5 deeds x 700
# + headings stay under 21,000 characters.
ID_MAX = 64
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
) -> list[RegionBrief]:
    """The regions the prompt shows, at most ``limit``, in this order (FD review R-06):
    the player's region, regions with an ACTIVE event, regions by active rumor count
    (most first), then the rest deepest level first — leaves before their parents, since
    events usually strike a place, not a realm. Ties keep the briefs' order."""
    order = {b.region_id: i for i, b in enumerate(briefs)}

    def depth(b: RegionBrief) -> int:
        rank = rank_of(b.level)
        return rank if rank is not None else 99

    def key(b: RegionBrief) -> tuple:
        if b.region_id == player_region_id:
            return (0, 0, 0, order[b.region_id])
        if b.region_id in event_region_ids:
            return (1, 0, 0, order[b.region_id])
        count = rumor_counts.get(b.region_id, 0)
        if count > 0:
            return (2, -count, 0, order[b.region_id])
        return (3, -depth(b), 0, order[b.region_id])

    return sorted(briefs, key=key)[: max(0, limit)]


def shown_name(name: str) -> str:
    """The region name exactly as the prompt shows it."""
    return one_line(name, NAME_MAX)


def region_line(b: RegionBrief) -> str:
    path = one_line(" > ".join(b.level_path), PATH_MAX)
    line = f"- {one_line(b.region_id, ID_MAX)}: {shown_name(b.name)}"
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
    return line[:DEED_LINE_MAX]


def suggestion_context(
    regions: Sequence[RegionBrief], events: Sequence[str], deeds: Sequence[str]
) -> str:
    """The context block of the suggestion prompt (BR-U7-9), at most ``CONTEXT_MAX``."""
    lines = [
        f"CONTEXT ({MATERIAL}):",
        "REGIONS (region_id: name (where) — description; known for):",
        *(region_line(b) for b in regions),
        "RECENT EVENTS:",
        *(events or ["- (none)"]),
        "RECENT DEEDS OF THE TRAVELER:",
        *(deeds or ["- (none)"]),
    ]
    return "\n".join(lines)[:CONTEXT_MAX]


def match_region(raw: str, regions: Sequence[RegionBrief]) -> str | None:
    """The region a suggestion names: its id, else its name as shown or in full (case and
    surrounding spaces ignored). A name that fits more than one region matches none."""
    wanted = raw.strip()
    for b in regions:
        if b.region_id == wanted:
            return b.region_id
    key = wanted.casefold()
    hits = {
        b.region_id
        for b in regions
        if key in (shown_name(b.name).casefold(), one_line(b.name).casefold())
    }
    return hits.pop() if len(hits) == 1 else None
