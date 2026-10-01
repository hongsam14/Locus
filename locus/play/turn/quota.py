"""Per-turn region quota — pure (U6 BLM §4, BR-U6-15/20, TP-U6-8).

One turn adds rumors to a region from three places — deed seeds, deed spread and
canonical drafts — before anything is saved. The active cap must count all three, so
they share this quota instead of each reading the stored count alone (FD review R-04).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping


class RegionQuota:
    def __init__(self, active: Mapping[str, int], cap: int) -> None:
        self._active = dict(active)  # stored active rumors per region at the turn's start
        self._cap = max(0, int(cap))
        self._added: Counter[str] = Counter()

    def full(self, region_id: str) -> bool:
        """No room left for one more rumor in ``region_id`` this turn."""
        return self._active.get(region_id, 0) + self._added[region_id] >= self._cap

    def add(self, region_id: str, n: int = 1) -> None:
        self._added[region_id] += n

    def reserved(self, region_id: str) -> int:
        """Rumors already added to ``region_id`` this turn but not saved yet."""
        return self._added[region_id]
