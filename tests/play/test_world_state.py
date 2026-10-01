"""U7 world state aggregation (FR-D4, BR-U7-18, TP-U7-7)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from locus.play.models import (
    EventCategory,
    EventStatus,
    RegionDistortion,
    SessionEvent,
    SessionRumor,
)
from locus.play.world_state import summarize_state
from locus.shared.models import Provenance, SourceKind
from tests.play.strategies import region

REGIONS = [region("a", name="Riverton"), region("b", name="Hollow"), region("c")]
_ids = st.sampled_from(["a", "b", "c", "gone"])


@st.composite
def _rumors(draw):
    return [
        SessionRumor(
            session_id="s",
            region_id=draw(_ids),
            distorted_from_id="k",
            promoted=draw(st.booleans()),
            active=draw(st.booleans()),
            origin_kind=draw(st.sampled_from(["canonical", "deed"])),
            provenance=Provenance(source=SourceKind.SIMULATION),
        )
        for _ in range(draw(st.integers(0, 15)))
    ]


@st.composite
def _events(draw):
    return [
        SessionEvent(
            session_id="s",
            region_id=draw(_ids),
            category=EventCategory.WAR,
            magnitude=0.5,
            status=draw(st.sampled_from(list(EventStatus))),
            provenance=Provenance(source=SourceKind.SIMULATION),
        )
        for _ in range(draw(st.integers(0, 6)))
    ]


@given(_rumors(), _events())
def test_tp_u7_7_one_row_per_world_region_and_the_counts_add_up(rumors, events) -> None:
    rows = summarize_state(REGIONS, [], rumors, events)
    assert [r.region_id for r in rows] == ["a", "b", "c"]
    live = [r for r in rumors if r.active and r.region_id != "gone"]
    assert sum(r.active_rumors for r in rows) == len(live)
    for row in rows:
        assert row.promoted_rumors <= row.active_rumors and row.deed_rumors <= row.active_rumors
    running = [e for e in events if e.status == "active" and e.region_id != "gone"]
    assert sum(r.active_events for r in rows) == len(running)


def test_br_u7_18_a_region_without_a_row_shows_the_default() -> None:
    stored = [
        RegionDistortion(session_id="s", region_id="a", distortion_degree=0.7, feedback_share=0.1)
    ]
    rows = {r.region_id: r for r in summarize_state(REGIONS, stored, [], [])}
    assert (rows["a"].distortion, rows["a"].feedback_share) == (0.7, 0.1)
    assert (rows["c"].distortion, rows["c"].feedback_share) == (0.3, 0.0)
    assert rows["a"].region_name == "Riverton"


# --- the service (Step 6.10): structure of the read (NFR-3) and a real session ------- #
def test_nfr3_state_is_five_store_reads_and_one_snapshot_read_whatever_the_regions() -> None:
    from locus.play import InMemoryPlayRepository
    from locus.play.models import Player
    from locus.play.world_state import WorldStateService
    from tests.play.strategies import build_snapshot
    from tests.shared.snapshots import StaticSnapshots

    repo = InMemoryPlayRepository()
    session = repo.create_session("w")
    repo.create_player(Player(session_id=session.id, name="Ari", region_id="r3"))
    calls: dict[str, int] = {}
    for name in (
        "get_session",
        "get_player",
        "list_region_distortions",
        "list_rumors",
        "list_events",
    ):
        real = getattr(repo, name)

        def counted(*a, _real=real, _name=name, **kw):
            calls[_name] = calls.get(_name, 0) + 1
            return _real(*a, **kw)

        setattr(repo, name, counted)
    snaps = StaticSnapshots(build_snapshot([f"r{i}" for i in range(12)], []))
    state = WorldStateService(repo, snaps).state(session.id)
    assert sum(calls.values()) == 5 and set(calls.values()) == {1}
    assert snaps.calls == 1
    assert len(state.regions) == 12 and state.player_region_id == "r3"
