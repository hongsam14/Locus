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
