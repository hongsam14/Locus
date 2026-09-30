"""U2 Q3=A — deterministic same-name resolution (TP-U2-5, EX-8; BR-U2-8/9)."""

from __future__ import annotations

import random

from hypothesis import given
from hypothesis import strategies as st

from locus.shared.models import Provenance, Region, RegionLevel, SourceKind
from locus.world.topology.naming import LEVEL_RANK, index_by_name, rank_of, resolve_region
from tests.world.strategies import same_name_regions


def _r(name: str, level: RegionLevel) -> Region:
    return Region(
        world_id="w", name=name, level=level, provenance=Provenance(source=SourceKind.INPUT)
    )


def test_level_rank_covers_every_hierarchy_level() -> None:  # EX-8
    assert set(RegionLevel) - {RegionLevel.TERRAIN} == set(LEVEL_RANK)
    assert rank_of(RegionLevel.TERRAIN) is None and rank_of("nope") is None
    assert LEVEL_RANK[RegionLevel.TOWN] < LEVEL_RANK[RegionLevel.DISTRICT]  # district inside town


@given(same_name_regions(), st.integers(min_value=0, max_value=10_000))
def test_resolution_is_order_independent_and_role_correct(data, seed: int) -> None:  # TP-U2-5
    name, regions = data
    shuffled = list(regions)
    random.Random(seed).shuffle(shuffled)
    by_a, by_b = index_by_name(regions), index_by_name(shuffled)

    hint_a, _ = resolve_region(name, by_a, role="hint")
    hint_b, _ = resolve_region(name, by_b, role="hint")
    assert (hint_a.id if hint_a else None) == (hint_b.id if hint_b else None)
    if hint_a is not None and len(regions) > 1:
        ranked = [r for r in regions if rank_of(r.level) is not None]
        if ranked:  # terrain never wins an ambiguous hint
            assert rank_of(hint_a.level) == max(rank_of(r.level) for r in ranked)

    for level in RegionLevel:  # explicit level -> exact level or nothing
        found, _ = resolve_region(name, by_a, role="hint", level=level)
        assert found is None or str(found.level) == str(level)

    for child in (RegionLevel.TOWN, RegionLevel.DISTRICT):  # parents are always broader
        parent, _ = resolve_region(name, by_a, role="parent", child_level=child)
        parent2, _ = resolve_region(name, by_b, role="parent", child_level=child)
        assert (parent.id if parent else None) == (parent2.id if parent2 else None)
        if parent is not None:
            assert rank_of(parent.level) < LEVEL_RANK[child]


def test_single_parent_candidate_still_needs_a_broader_level() -> None:
    town = _r("Riverton", RegionLevel.TOWN)
    parent, warning = resolve_region(
        "Riverton", index_by_name([town]), role="parent", child_level=RegionLevel.TOWN
    )
    assert parent is None and warning is not None and "no parent-level" in warning.message


def test_ambiguous_choices_are_reported() -> None:
    prov, town = _r("Riverton", RegionLevel.PROVINCE), _r("Riverton", RegionLevel.TOWN)
    by_name = index_by_name([prov, town])
    hint, warning = resolve_region("riverton", by_name, role="hint")
    assert hint is town and warning is not None and "most specific" in warning.message
    parent, warning = resolve_region(
        "Riverton", by_name, role="parent", child_level=RegionLevel.DISTRICT
    )
    assert parent is town and warning is not None and "ambiguous parent" in warning.message
    parent, _ = resolve_region("Riverton", by_name, role="parent", child_level=RegionLevel.TOWN)
    assert parent is prov
    missing, warning = resolve_region("Nowhere", by_name, role="hint")
    assert missing is None and "unresolved" in warning.message
