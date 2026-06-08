"""Bundled real-world sample for Wiki bootstrapping (U6, Q2=C).

A tiny Earth-like reference (memo + structured map) so ``build-wiki`` works
out of the box; users can add their own real-world materials on top (append).
"""

from __future__ import annotations

from ..ingestion.service import WorldInputs

_REALWORLD_MEMO = """
Real-world geography priors:
- A mountain range between two regions slows travel and the exchange of news;
  cultures on either side diverge.
- A basin (low land ringed by higher terrain) traps heat and tends to be hot and
  arid, like Death Valley.
- Rivers enable trade and tend to concentrate settlements along their banks.
- Coastal regions trade by sea and share goods and rumors with distant ports.
- Deserts isolate the regions they separate; crossing is slow and dangerous.
""".strip()

_REALWORLD_MAP = {
    "regions": [
        {"name": "Highlands", "level": "province", "attributes": {"terrain": "mountain"}},
        {"name": "Sun Basin", "level": "province", "attributes": {"terrain": "basin"}},
        {"name": "River Vale", "level": "province", "attributes": {"terrain": "river"}},
        {"name": "Port Coast", "level": "province", "attributes": {"terrain": "coast"}},
    ],
    "connections": [
        {"from": "Highlands", "to": "Sun Basin", "kind": "blocked"},
        {"from": "River Vale", "to": "Port Coast", "kind": "route"},
    ],
}


def load_bundled_realworld() -> WorldInputs:
    """Return the bundled real-world inputs (memo + structured map)."""
    return WorldInputs(memos=[_REALWORLD_MEMO], structured_maps=[_REALWORLD_MAP])
