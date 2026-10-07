"""Deterministic region-name resolution (U2 Q3=A, BR-U2-8/9, RE A11).

Same-name regions of different levels ("Ford" the town and "Ford" the
province) used to resolve to whichever came last in a dict. One rule, one place:

- a hint that names a level matches that level exactly, or nothing;
- a single candidate wins — except a *parent* must still be a broader level than
  the child;
- parent role: the broadest-but-closest level above the child;
- hint role (connection / knowledge): the most specific level;
- ties are fixed by (name, id); every ambiguous choice is reported.

``RegionLevel.TERRAIN`` (VLM-promoted terrain) is not a hierarchy level: it is
absent from ``LEVEL_RANK`` and never wins an ambiguous choice.
"""

from __future__ import annotations

from typing import Literal

from locus.shared.models import BuildWarning, Region, RegionLevel
from locus.shared.models.util import LEVEL_RANK, index_by_name, normalize_name, rank_of

Role = Literal["parent", "hint"]

__all__ = ["LEVEL_RANK", "index_by_name", "rank_of", "resolve_region"]


def _warn(stage: str, message: str, item_id: str | None = None) -> BuildWarning:
    return BuildWarning(stage=stage, item_id=item_id, message=message, severity="warning")


def _pick(cands: list[Region]) -> Region:
    return sorted(cands, key=lambda r: (r.name, r.id))[0]


def resolve_region(
    name: str,
    by_name: dict[str, list[Region]],
    *,
    role: Role,
    child_level: RegionLevel | str | None = None,
    level: RegionLevel | str | None = None,
    stage: str = "topology",
) -> tuple[Region | None, BuildWarning | None]:
    """Resolve ``name`` against ``by_name`` (from ``index_by_name``); see module doc."""
    cands = by_name.get(normalize_name(name), [])
    if not cands:
        return None, _warn(stage, f"unresolved region name: {name!r}")
    if level is not None:  # (a) explicit level -> exact match only
        exact = [c for c in cands if str(c.level) == str(level)]
        if exact:
            return _pick(exact), None
        return None, _warn(stage, f"no region {name!r} at level {str(level)!r}")
    if role == "parent":
        if child_level is None:
            raise ValueError("role='parent' needs child_level")
        child_rank = rank_of(child_level)
        above = [
            c
            for c in cands
            if rank_of(c.level) is not None
            and child_rank is not None
            and rank_of(c.level) < child_rank  # type: ignore[operator]
        ]
        if not above:
            return None, _warn(
                stage, f"no parent-level candidate for {name!r} above {str(child_level)!r}"
            )
        best = max(rank_of(c.level) for c in above)  # type: ignore[type-var]
        chosen = _pick([c for c in above if rank_of(c.level) == best])
        if len(cands) == 1:
            return chosen, None
        return chosen, _warn(
            stage, f"ambiguous parent {name!r}: chose level {str(chosen.level)!r}", chosen.id
        )
    # role == "hint"
    if len(cands) == 1:
        return cands[0], None
    ranked = [c for c in cands if rank_of(c.level) is not None]
    if not ranked:
        chosen = _pick(cands)
        return chosen, _warn(stage, f"ambiguous hint {name!r} among terrain regions", chosen.id)
    best = max(rank_of(c.level) for c in ranked)  # type: ignore[type-var]
    chosen = _pick([c for c in ranked if rank_of(c.level) == best])
    return chosen, _warn(
        stage,
        f"ambiguous hint {name!r}: chose most specific level {str(chosen.level)!r}",
        chosen.id,
    )
