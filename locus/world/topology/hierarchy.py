"""Region hierarchy assignment (U3, US-2.1, FD3-Q1=A; U2 Q3=A).

Pure: resolves ``attributes['parent_name']`` to ``parent_id`` (CONTAINS) through
``resolve_region`` (role=parent: the parent must be a broader level than the
child, same-name candidates are chosen deterministically), leaves unmatched
regions at top level, and guards against cycles (BR-U3-2/3/4, BR-U2-8).
"""

from __future__ import annotations

from locus.shared.models import BuildWarning, Region
from locus.world.topology.naming import index_by_name, resolve_region


def assign_hierarchy(regions: list[Region]) -> tuple[list[Region], list[BuildWarning]]:
    """Set ``parent_id`` from ``attributes['parent_name']``.

    Returns (regions, warnings). Regions are mutated in place and returned.
    """
    warnings: list[BuildWarning] = []
    by_name = index_by_name(regions)

    for r in regions:
        parent_name = r.attributes.get("parent_name")
        if not parent_name:
            r.parent_id = None
            continue
        parent, warning = resolve_region(
            parent_name, by_name, role="parent", child_level=r.level, stage="topology"
        )
        if warning is not None:
            warning.item_id = warning.item_id or r.id
            warnings.append(warning)
        if parent is None or parent.id == r.id:
            r.parent_id = None
            if parent is not None:
                warnings.append(
                    BuildWarning(
                        stage="topology",
                        item_id=r.id,
                        message=f"region '{r.name}': self-parent ignored",
                    )
                )
            continue
        r.parent_id = parent.id

    _break_cycles(regions, warnings)
    return regions, warnings


def _break_cycles(regions: list[Region], warnings: list[BuildWarning]) -> None:
    by_id = {r.id: r for r in regions}
    for r in regions:
        seen = set()
        cur = r
        while cur.parent_id is not None:
            if cur.parent_id in seen or cur.parent_id == r.id:
                warnings.append(
                    BuildWarning(
                        stage="topology",
                        item_id=r.id,
                        message=f"region '{r.name}': cycle detected; parent link cut",
                    )
                )
                r.parent_id = None
                break
            seen.add(cur.parent_id)
            cur = by_id.get(cur.parent_id)
            if cur is None:
                break
