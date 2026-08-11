"""S1 session model tests — validation + property-based round-trip (NFR-R5)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from locus.models import Provenance, SourceKind
from locus.session.models import (
    DEFAULT_DISTORTION_DEGREE,
    GameSession,
    RegionDistortion,
    SessionRumor,
    SessionStatus,
    TimelineEntry,
    TimelineKind,
)


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def test_gamesession_defaults() -> None:
    s = GameSession(world_id="w")
    assert s.status == SessionStatus.OPEN.value
    assert s.turn == 0
    assert s.created_at is None and s.closed_at is None
    assert s.id  # auto uuid


def test_default_distortion_degree_constant() -> None:
    assert DEFAULT_DISTORTION_DEGREE == 0.3
    assert RegionDistortion(session_id="s", region_id="r").distortion_degree == 0.3


@pytest.mark.parametrize("bad", [-0.1, 1.1])
def test_rumor_range_validation(bad: float) -> None:
    for field in ("distortion_degree", "support", "confidence"):
        with pytest.raises(ValidationError):
            SessionRumor(
                session_id="s",
                region_id="r",
                distorted_from_id="k",
                provenance=_prov(),
                **{field: bad},
            )


def test_session_rumor_roundtrip() -> None:
    r = SessionRumor(
        session_id="s",
        region_id="r",
        distorted_from_id="k1",
        distorted_from_kind="knowledge",
        statement="a distorted tale",
        distortion_degree=0.5,
        support=0.7,
        confidence=0.5,
        promoted=True,
        provenance=_prov(),
    )
    assert SessionRumor.model_validate(r.model_dump()) == r


def test_timeline_entry_roundtrip() -> None:
    e = TimelineEntry(
        session_id="s",
        turn=2,
        kind=TimelineKind.GENERATE,
        summary="generated 3 rumors",
        payload={"rumor_ids": ["a", "b", "c"]},
    )
    assert TimelineEntry.model_validate(e.model_dump()) == e


@given(
    degree=st.floats(min_value=0.0, max_value=1.0),
    support=st.floats(min_value=0.0, max_value=1.0),
    confidence=st.floats(min_value=0.0, max_value=1.0),
)
def test_rumor_pbt_roundtrip(degree: float, support: float, confidence: float) -> None:
    r = SessionRumor(
        session_id="s",
        region_id="r",
        distorted_from_id="k",
        distortion_degree=degree,
        support=support,
        confidence=confidence,
        provenance=_prov(),
    )
    assert SessionRumor.model_validate(r.model_dump()) == r
