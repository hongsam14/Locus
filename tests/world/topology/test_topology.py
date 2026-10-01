"""U3 Topology tests — weights, hierarchy, candidates, build (mock Wiki)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from locus.shared.models import (
    IngestionResult,
    PriorType,
    Provenance,
    Region,
    RegionLevel,
    SourceKind,
    WikiPrior,
)
from locus.world.topology import TopologyBuilder, assign_hierarchy, compute_weight
from locus.world.topology.builder import collect_connection_candidates


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def _region(name: str, level: RegionLevel, parent: str | None = None) -> Region:
    attrs = {"parent_name": parent} if parent else {}
    return Region(world_id="w", name=name, level=level, attributes=attrs, provenance=_prov())


# --------------------------------------------------------------------------- #
# Weights
# --------------------------------------------------------------------------- #
def test_compute_weight_blocked_mountain() -> None:
    assert abs(compute_weight("blocked", ["mountain"]) - 0.08) < 1e-9


def test_compute_weight_route_road_clamped() -> None:
    # 0.6 * 1.2 = 0.72
    assert abs(compute_weight("route", ["road"]) - 0.72) < 1e-9


@given(
    kind=st.sampled_from(["adjacent", "route", "river", "blocked", "unknown"]),
    terrains=st.lists(st.sampled_from(["mountain", "river", "road", "sea", "x"]), max_size=4),
)
def test_compute_weight_in_range(kind: str, terrains: list[str]) -> None:
    assert 0.0 <= compute_weight(kind, terrains) <= 1.0


# --------------------------------------------------------------------------- #
# Hierarchy
# --------------------------------------------------------------------------- #
def test_assign_hierarchy_links_parent() -> None:
    cont = _region("Northland", RegionLevel.CONTINENT)
    town = _region("Rivertown", RegionLevel.TOWN, parent="Northland")
    regions, warnings = assign_hierarchy([cont, town])
    assert town.parent_id == cont.id
    assert cont.parent_id is None
    assert not warnings


def test_assign_hierarchy_orphan_kept_top_level() -> None:
    town = _region("Lonely", RegionLevel.TOWN, parent="Nowhere")
    _, warnings = assign_hierarchy([town])
    assert town.parent_id is None
    assert warnings


def test_assign_hierarchy_breaks_cycle() -> None:
    a = _region("A", RegionLevel.PROVINCE, parent="B")
    b = _region("B", RegionLevel.PROVINCE, parent="A")
    assign_hierarchy([a, b])
    # at least one link must be cut to avoid a cycle
    assert (a.parent_id is None) or (b.parent_id is None)


# --------------------------------------------------------------------------- #
# Connection candidates
# --------------------------------------------------------------------------- #
def test_collect_candidates_resolves_and_dedupes() -> None:
    a = _region("A", RegionLevel.TOWN)
    b = _region("B", RegionLevel.TOWN)
    a.attributes["connection_hints"] = [
        {"from": "A", "to": "B", "kind": "route"},
        {"from": "B", "to": "A", "kind": "route"},  # duplicate unordered pair
    ]
    cands, warnings = collect_connection_candidates([a, b])
    assert len(cands) == 1


def test_collect_candidates_unresolved_warns() -> None:
    a = _region("A", RegionLevel.TOWN)
    a.attributes["connection_hints"] = [{"from": "A", "to": "Ghost", "kind": "route"}]
    cands, warnings = collect_connection_candidates([a])
    assert cands == []
    assert warnings


# --------------------------------------------------------------------------- #
# Build (mock Wiki)
# --------------------------------------------------------------------------- #
class _FakeWiki:
    def lookup_terrain_rule(self, feature: str):
        return [
            WikiPrior(
                id="prior-1",
                world_id="w",
                prior_type=PriorType.TERRAIN_RULE,
                condition=f"{feature} between regions",
                effect="slower exchange",
                provenance=Provenance(source=SourceKind.INPUT, generated_by="wiki"),
            )
        ]


def test_build_creates_symmetric_weighted_edges() -> None:
    a = _region("A", RegionLevel.TOWN)
    b = _region("B", RegionLevel.TOWN)
    a.attributes["connection_hints"] = [
        {"from": "A", "to": "B", "kind": "blocked", "terrain_kind": "mountain"}
    ]
    ingestion = IngestionResult(world_id="w", region_hints=[a, b])

    topo = TopologyBuilder(wiki=_FakeWiki()).build(ingestion, world_id="w").topology

    assert len(topo.connections) == 2  # symmetric
    fwd = next(c for c in topo.connections if c.source_region_id == a.id)
    assert abs(fwd.weight - 0.08) < 1e-9  # blocked(0.2) * mountain(0.4)
    assert fwd.rationale == "slower exchange"
    assert fwd.wiki_prior_ref == "prior-1"
    assert fwd.provenance.source == SourceKind.INFERRED


def test_build_without_wiki_uses_base_weight() -> None:
    a = _region("A", RegionLevel.TOWN)
    b = _region("B", RegionLevel.TOWN)
    a.attributes["connection_hints"] = [{"from": "A", "to": "B", "kind": "route"}]
    ingestion = IngestionResult(world_id="w", region_hints=[a, b])

    topo = TopologyBuilder(wiki=None).build(ingestion, world_id="w").topology
    assert len(topo.connections) == 2
    assert abs(topo.connections[0].weight - 0.6) < 1e-9


# --------------------------------------------------------------------------- #
# U2 Step 7 — warnings ride along in TopologyBuild (RE A13)
# --------------------------------------------------------------------------- #
def test_topology_build_carries_hierarchy_and_hint_warnings() -> None:
    from locus.shared.models import IngestionResult

    town = _region("Lonely", RegionLevel.TOWN, parent="Nowhere")
    town.attributes["connection_hints"] = [{"from": "Lonely", "to": "Ghost", "kind": "route"}]
    result = TopologyBuilder(wiki=None).build(
        IngestionResult(world_id="w", region_hints=[town]), world_id="w"
    )
    assert len(result.topology.regions) == 1 and result.topology.connections == []
    messages = [w.message for w in result.warnings]
    assert any("Nowhere" in m for m in messages) and any("Ghost" in m for m in messages)
    assert all(w.severity == "warning" and w.stage == "topology" for w in result.warnings)


# --- U7 (FR-A7, US-8.5): the weight table is a tuning, not a constant --------------- #
def test_u7_compute_weight_reads_the_given_tuning() -> None:
    from types import MappingProxyType

    from locus.shared.config.tuning import WorldTuning

    tuned = WorldTuning(
        base_weights=MappingProxyType({"route": 0.9}),
        terrain_modifiers=MappingProxyType({"swamp": 0.5}),
    )
    assert compute_weight("route", ["swamp"], tuning=tuned) == 0.45
    # U3 intended change: A3-15 — no default_base; a kind missing from the table falls to
    # the adjacent weight (the builder maps unknown kinds to adjacent before this)
    assert compute_weight("river", [], tuning=tuned) == 0.8
    assert compute_weight("route", ["swamp"]) == 0.6  # defaults: no swamp modifier
