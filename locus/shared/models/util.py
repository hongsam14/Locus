"""Tiny pure helpers shared by every boundary (U1 §13.2)."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TYPE_CHECKING

from locus.shared.models.enums import RegionLevel

if TYPE_CHECKING:  # pragma: no cover
    from locus.shared.models.graph import Region

_WS_RE = re.compile(r"\s+")


def clamp01(value: float) -> float:
    """Clamp a degree / support / weight / coordinate to the [0, 1] domain."""
    return max(0.0, min(1.0, value))


def normalize_name(name: str) -> str:
    """Lowercase + collapse whitespace: the dedup / lookup key for names (BR-U2-4)."""
    return _WS_RE.sub(" ", name.strip().lower())


def index_by_name(regions: "Iterable[Region]") -> dict[str, list["Region"]]:
    """Group regions by normalized name; same-name regions of different levels share a key
    (the input to ``resolve_region``, U2 Q3=A)."""
    out: dict[str, list["Region"]] = {}
    for r in regions:
        out.setdefault(normalize_name(r.name), []).append(r)
    return out


# Region hierarchy order, broad -> specific; explicit so enum declaration order cannot
# change resolution or sorting. TERRAIN (VLM-promoted terrain) is not a hierarchy level.
LEVEL_RANK: dict[RegionLevel, int] = {
    RegionLevel.CONTINENT: 0,
    RegionLevel.PROVINCE: 1,
    RegionLevel.TOWN: 2,
    RegionLevel.DISTRICT: 3,
}


def rank_of(level: "RegionLevel | str") -> int | None:
    try:
        return LEVEL_RANK.get(RegionLevel(str(level)))
    except ValueError:
        return None
