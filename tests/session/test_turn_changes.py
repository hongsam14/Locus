"""Pure shape_region_changes tests (X1 / BR-X1-19/20/21) + PBT."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from locus.session.turn_changes import shape_region_changes


def test_groups_by_region_and_omits_unchanged() -> None:
    out = shape_region_changes(
        promoted=["ra"],
        demoted=[],
        pruned=["rb"],
        applied_events=["e1"],
        resolved_events=[],
        added_by_region={"R2": ["rc"]},
        rumor_region={"ra": "R1", "rb": "R1", "rc": "R2"},
        event_region={"e1": "R2"},
    )
    by_region = {rc.region_id: rc for rc in out}
    assert set(by_region) == {"R1", "R2"}
    assert by_region["R1"].promoted == ["ra"] and by_region["R1"].pruned == ["rb"]
    assert by_region["R2"].rumors_added == ["rc"] and by_region["R2"].events_applied == ["e1"]


def test_empty_input_yields_no_changes() -> None:
    assert (
        shape_region_changes(
            promoted=[],
            demoted=[],
            pruned=[],
            applied_events=[],
            resolved_events=[],
            added_by_region={},
            rumor_region={},
            event_region={},
        )
        == []
    )


def test_unknown_region_ids_are_skipped() -> None:
    out = shape_region_changes(
        promoted=["ghost"],
        demoted=[],
        pruned=[],
        applied_events=[],
        resolved_events=[],
        added_by_region={},
        rumor_region={},  # no mapping for "ghost"
        event_region={},
    )
    assert out == []


@given(
    promoted=st.lists(st.sampled_from(["r1", "r2", "r3"]), max_size=5, unique=True),
    pruned=st.lists(st.sampled_from(["r1", "r2", "r3"]), max_size=5, unique=True),
)
def test_every_emitted_region_has_a_change(promoted, pruned) -> None:
    rumor_region = {"r1": "A", "r2": "A", "r3": "B"}
    out = shape_region_changes(
        promoted=promoted,
        demoted=[],
        pruned=pruned,
        applied_events=[],
        resolved_events=[],
        added_by_region={},
        rumor_region=rumor_region,
        event_region={},
    )
    for rc in out:  # BR-X1-21: no empty region emitted
        assert (
            rc.promoted
            or rc.demoted
            or rc.pruned
            or rc.rumors_added
            or (rc.events_applied or rc.events_resolved)
        )
