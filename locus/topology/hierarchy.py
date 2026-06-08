"""Region hierarchy assignment (U3, US-2.1, FD3-Q1=A).

Pure: resolves ``attributes['parent_name']`` to ``parent_id`` (CONTAINS), leaves
unmatched regions at top level, and guards against cycles (BR-U3-2/3/4).
"""

from __future__ import annotations

from ..models import Region


def _norm(name: str) -> str:
    return " ".join(name.strip().lower().split())


def assign_hierarchy(regions: list[Region]) -> tuple[list[Region], list[str]]:
    """Set ``parent_id`` from ``attributes['parent_name']``.

    Returns (regions, warnings). Regions are mutated in place and returned.
    """
    warnings: list[str] = []
    by_name: dict[str, Region] = {_norm(r.name): r for r in regions}

    for r in regions:
        parent_name = r.attributes.get("parent_name")
        if not parent_name:
            r.parent_id = None
            continue
        parent = by_name.get(_norm(parent_name))
        if parent is None:
            r.parent_id = None
            warnings.append(f"region '{r.name}': parent '{parent_name}' not found; kept top-level")
            continue
        if parent.id == r.id:
            r.parent_id = None
            warnings.append(f"region '{r.name}': self-parent ignored")
            continue
        r.parent_id = parent.id

    _break_cycles(regions, warnings)
    return regions, warnings


def _break_cycles(regions: list[Region], warnings: list[str]) -> None:
    by_id = {r.id: r for r in regions}
    for r in regions:
        seen = set()
        cur = r
        while cur.parent_id is not None:
            if cur.parent_id in seen or cur.parent_id == r.id:
                warnings.append(f"region '{r.name}': cycle detected; parent link cut")
                r.parent_id = None
                break
            seen.add(cur.parent_id)
            cur = by_id.get(cur.parent_id)
            if cur is None:
                break
