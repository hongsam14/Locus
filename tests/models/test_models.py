"""U1 model tests — validation + property-based round-trip (NFR-C2, BR-20/21)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from locus.models import (
    Entity,
    EntityType,
    Knowledge,
    Provenance,
    Region,
    RegionLevel,
    Rumor,
    SourceKind,
)


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


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
        world_id="w1", statement=statement, confidence=confidence, topic=topic, provenance=_prov()
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


@given(degree=st.floats(min_value=0.0, max_value=1.0))
def test_rumor_roundtrip(degree: float) -> None:
    rumor = Rumor(
        world_id="w1",
        statement="distorted",
        distorted_from_id="k-origin",
        distortion_degree=degree,
        provenance=_prov(),
    )
    assert Rumor.model_validate(rumor.model_dump()) == rumor


# --------------------------------------------------------------------------- #
# Validation (BR-4..6)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", [-0.1, 1.1, 2.0])
def test_confidence_out_of_range_rejected(bad: float) -> None:
    with pytest.raises(ValidationError):
        Knowledge(world_id="w1", statement="x", confidence=bad, provenance=_prov())


def test_extra_field_forbidden() -> None:
    with pytest.raises(ValidationError):
        Entity(
            world_id="w1",
            name="x",
            entity_type=EntityType.PLACE,
            provenance=_prov(),
            bogus="nope",  # type: ignore[call-arg]
        )


# --------------------------------------------------------------------------- #
# Rumor invariants (BR-13)
# --------------------------------------------------------------------------- #
def test_rumor_requires_origin() -> None:
    with pytest.raises(ValidationError):
        Rumor(world_id="w1", statement="x", provenance=_prov())  # type: ignore[call-arg]


def test_enum_serializes_to_string() -> None:
    e = Entity(world_id="w1", name="Town", entity_type=EntityType.PLACE, provenance=_prov())
    dumped = e.model_dump()
    assert dumped["entity_type"] == "place"  # BR-21 stable string value
