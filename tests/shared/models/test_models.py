"""U1 model tests — validation + property-based round-trip (NFR-C2, BR-20/21)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from locus.shared.models import (
    Entity,
    EntityType,
    Knowledge,
    PriorType,
    Provenance,
    Region,
    RegionLevel,
    SourceKind,
    WikiDomain,
    WikiPrior,
    WikiPriorLink,
    fallback_title,
)


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def test_fallback_title_truncates_on_word_boundary() -> None:
    assert fallback_title("Short one") == "Short one"
    long = "the quick brown fox jumps over the lazy dog and keeps on running far away today"
    out = fallback_title(long, max_len=20)
    assert len(out) <= 21 and out.endswith("…")
    assert " " in out and not out.startswith(" ")
    assert fallback_title("   ") == "(untitled)"


def test_wikiprior_requires_world_id_and_roundtrips_domains() -> None:
    p = WikiPrior(
        world_id="w",
        prior_type=PriorType.FACT,
        condition="c",
        effect="e",
        domains=[WikiDomain.GEOGRAPHY, WikiDomain.ECONOMY],
        provenance=_prov(),
    )
    assert WikiPrior.model_validate(p.model_dump()) == p
    with pytest.raises(ValidationError):
        WikiPrior(prior_type=PriorType.FACT, condition="c", effect="e", provenance=_prov())


def test_wikipriorlink_roundtrip() -> None:
    link = WikiPriorLink(
        world_id="w",
        source_id="a",
        target_id="b",
        relation="implies",
        weight=0.7,
        provenance=_prov(),
    )
    assert WikiPriorLink.model_validate(link.model_dump()) == link


# --------------------------------------------------------------------------- #
# Property-based: serialization round-trip (BR-20/21)
# --------------------------------------------------------------------------- #
@given(
    statement=st.text(min_size=1, max_size=200),
    confidence=st.floats(min_value=0.0, max_value=1.0),
    topic=st.one_of(st.none(), st.text(max_size=50)),
)
def test_knowledge_roundtrip(statement: str, confidence: float, topic: str | None) -> None:
    k = Knowledge(
        world_id="w1",
        statement=statement,
        title=statement,
        confidence=confidence,
        topic=topic,
        provenance=_prov(),
    )
    assert Knowledge.model_validate(k.model_dump()) == k
    # JSON round-trip too
    assert Knowledge.model_validate_json(k.model_dump_json()) == k


@given(
    name=st.text(min_size=1, max_size=100),
    level=st.sampled_from(list(RegionLevel)),
)
def test_region_roundtrip(name: str, level: RegionLevel) -> None:
    r = Region(world_id="w1", name=name, level=level, provenance=_prov())
    assert Region.model_validate(r.model_dump()) == r


# --------------------------------------------------------------------------- #
# Validation (BR-4..6)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", [-0.1, 1.1, 2.0])
def test_confidence_out_of_range_rejected(bad: float) -> None:
    with pytest.raises(ValidationError):
        Knowledge(world_id="w1", statement="x", title="x", confidence=bad, provenance=_prov())


def test_extra_field_forbidden() -> None:
    with pytest.raises(ValidationError):
        Entity(
            world_id="w1",
            name="x",
            entity_type=EntityType.PLACE,
            provenance=_prov(),
            bogus="nope",  # type: ignore[call-arg]
        )


def test_enum_serializes_to_string() -> None:
    e = Entity(world_id="w1", name="Town", entity_type=EntityType.PLACE, provenance=_prov())
    dumped = e.model_dump()
    assert dumped["entity_type"] == "place"  # BR-21 stable string value


# --- review U1 #1/#2: values persisted before the SourceKind rename stay readable ---
def test_legacy_source_kind_values_map_to_current_members() -> None:
    from locus.shared.models import Provenance, SourceKind

    assert SourceKind("inferred-wiki") is SourceKind.INFERRED
    assert SourceKind("session-rumor") is SourceKind.SIMULATION
    assert SourceKind("session-event") is SourceKind.SIMULATION
    # LocusModel stores enum values, so compare by value
    assert Provenance.model_validate({"source": "session-rumor"}).source == SourceKind.SIMULATION
    with pytest.raises(ValueError):
        SourceKind("no-such-kind")


def test_legacy_neo4j_prov_source_loads() -> None:
    from locus.shared.models import SourceKind
    from locus.shared.storage import graph_mapping as gm
    from locus.shared.storage.base import Node

    node = Node(
        id="k1",
        label="Knowledge",
        world_id="w",
        properties={
            "id": "k1",
            "world_id": "w",
            "statement": "s",
            "title": "t",
            "prov_source": "inferred-wiki",
        },
    )
    assert gm.node_to_knowledge(node).provenance.source == SourceKind.INFERRED


# --- U2 Step 2: WorldMeta / NPC / WorldSnapshot / report severity --------------- #
from hypothesis import given as _given  # noqa: E402

from locus.shared.models import (  # noqa: E402
    NPC,
    BuildReport,
    BuildWarning,
    ImportReport,
    KnowledgeGraph,
    RegionTopology,
    WorldMeta,
    WorldSnapshot,
)
from locus.shared.models.util import index_by_name  # noqa: E402

_names = st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=1, max_size=20).filter(
    lambda s: s.strip()
)


@_given(name=_names, role=_names, traits=st.lists(_names, max_size=3))
def test_npc_roundtrip(name: str, role: str, traits: list[str]) -> None:
    npc = NPC(
        world_id="w",
        name=name,
        role=role,
        description="d",
        home_region_id="r1",
        traits=traits,
        provenance=_prov(),
    )
    assert NPC.model_validate(npc.model_dump()) == npc
    assert NPC.model_validate_json(npc.model_dump_json()) == npc


def test_worldmeta_defaults_and_roundtrip() -> None:
    meta = WorldMeta(id="w", name="World")
    assert meta.format_version == 1 and meta.last_writer == "build"
    assert WorldMeta.model_validate_json(meta.model_dump_json()) == meta


def test_world_snapshot_indexes_regions_and_npcs() -> None:
    a = Region(world_id="w", name="Riverton", level=RegionLevel.TOWN, provenance=_prov())
    b = Region(world_id="w", name="riverton ", level=RegionLevel.PROVINCE, provenance=_prov())
    npc = NPC(
        world_id="w",
        name="Tomas",
        role="mayor",
        description="d",
        home_region_id=a.id,
        provenance=_prov(),
    )
    k = Knowledge(world_id="w", statement="s", title="t", provenance=_prov())
    snap = WorldSnapshot(
        world_id="w",
        kg=KnowledgeGraph(world_id="w", knowledge=[k], unscoped_knowledge_ids=[k.id]),
        topo=RegionTopology(world_id="w", regions=[a, b]),
        npcs=[npc],
    )
    assert snap.regions_by_id[a.id] is a
    assert [r.id for r in snap.regions_by_name["riverton"]] == [a.id, b.id]  # same-name candidates
    assert snap.npcs_by_region[a.id] == [npc] and snap.npcs_by_region.get(b.id) is None
    assert snap.unscoped_knowledge_ids == [k.id]
    assert index_by_name([a, b]) == snap.regions_by_name


def test_build_report_ok_follows_severity() -> None:
    warn = BuildWarning(stage="topology", message="ambiguous")
    err = BuildWarning(stage="persist-graph", message="boom", severity="error")
    assert BuildReport(world_id="w", warnings=[warn]).ok is True
    report = BuildReport(world_id="w", warnings=[warn, err])
    assert report.ok is False and report.errors == [err]
    assert report.model_dump()["ok"] is False  # serialized for the API/UI
    assert (
        ImportReport(world_id="w", format_version=1, source_world_id="w", warnings=[err]).ok
        is False
    )
