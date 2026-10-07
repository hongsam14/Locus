"""U3 code-review-01 items closed in U8 Step 9d (play).

#10 a GM set never revives or undoes a resolve · S17 only the provider call is an LLM
failure · S18 born and spread support is stored settled · C16 a resolve names its
region before the transaction.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine

from locus.play import InMemoryPlayRepository
from locus.play.models import DeclareAction, EventCategory, EventStatus
from locus.play.rumor.spread import plan_spread
from locus.play.storage.postgres_repo import PostgresPlayRepository
from locus.shared.config.tuning import PlayTuning
from tests.play.strategies import build_snapshot, deed_rumor, edge
from tests.play.test_deed_turns import _setup as _deed_setup
from tests.play.test_u3_carry import _setup as _carry_setup
from tests.play.test_u3_carry import _war_with_contribution


def _resolved_stale_copy(repo, session_id: str, event_id: str):
    """The event as a set that read it before a resolve committed would hold it."""
    stale = repo.get_event(session_id, event_id)
    assert stale is not None and stale.status == EventStatus.ACTIVE.value
    return stale


def test_10_a_set_that_read_before_a_resolve_cannot_revive_it() -> None:
    """The race of the review, made deterministic: the set's read returns the event as it
    was before the resolve (ACTIVE); its write must not bring it back."""
    repo, loader, gm, session = _carry_setup()
    rid = loader.region.id
    event = _war_with_contribution(repo, gm, session, rid, 0.3)
    stale = _resolved_stale_copy(repo, session.id, event.id)
    gm.events.resolve_event(session.id, event.id)
    real = repo.list_events
    repo.list_events = lambda sid, status=None, **kw: [stale]  # type: ignore[method-assign]
    try:
        gm.distortions.set_region_distortion(session.id, rid, 0.5)
    finally:
        repo.list_events = real  # type: ignore[method-assign]
    assert repo.get_event(session.id, event.id).status == EventStatus.RESOLVED.value
    line = [t for t in repo.list_timeline(session.id) if t.kind == "set_distortion"][-1]
    assert line.payload["event_contributions_cleared"] == 0.0  # nothing was cleared


@pytest.mark.parametrize("make", ["memory", "sqlite"])
def test_10_contributions_are_written_only_while_the_event_is_active(make) -> None:
    if make == "memory":
        repo = InMemoryPlayRepository()
    else:
        repo = PostgresPlayRepository(engine=create_engine("sqlite://", future=True))
        repo.ensure_schema()
    session = repo.create_session("w")
    from locus.play.models import SessionEvent
    from locus.shared.models import Provenance, SourceKind

    ev = repo.create_event(
        SessionEvent(
            session_id=session.id,
            region_id="r1",
            category=EventCategory.WAR,
            magnitude=0.5,
            contributions={"r1": 0.3, "r2": 0.2},
            provenance=Provenance(source=SourceKind.SIMULATION),
        )
    )
    active = EventStatus.ACTIVE.value
    assert repo.update_event_contributions(session.id, ev.id, {"r2": 0.2}, status=active)
    assert repo.get_event(session.id, ev.id).contributions == {"r2": 0.2}
    ev = repo.get_event(session.id, ev.id)
    ev.status = EventStatus.RESOLVED.value
    repo.update_event(ev)
    assert not repo.update_event_contributions(session.id, ev.id, {}, status=active)
    after = repo.get_event(session.id, ev.id)
    assert after.status == EventStatus.RESOLVED.value and after.contributions == {"r2": 0.2}
    assert repo.list_events(session.id, active, for_update=True) == []  # the flag is accepted


def test_c16_a_resolve_names_its_region_once_before_the_transaction() -> None:
    repo, loader, gm, session = _carry_setup()
    event = _war_with_contribution(repo, gm, session, loader.region.id, 0.3)
    names: list[str] = []
    real = gm.events._region_name
    gm.events._region_name = lambda s, rid: (names.append(rid), real(s, rid))[1]  # type: ignore[method-assign]
    gm.events.resolve_event(session.id, event.id)
    assert names == [loader.region.id]


def test_s17_a_prompt_bug_is_the_runs_failure_not_the_llms() -> None:
    repo, gm, session, _p, voice, _r, _w = _deed_setup()
    narrator = gm.turns._narrator

    def broken(**kw):
        raise KeyError("template field")

    narrator.prompts = broken  # type: ignore[method-assign]
    with pytest.raises(KeyError):
        gm.turns.advance(session.id, DeclareAction(text="sing a song"), lang="en")
    assert voice.structured_calls == []  # no provider call was made or booked as one


def test_s18_a_spread_hop_is_stored_settled() -> None:
    """0.6 x (0.5 + 0.5 x 0.5) is 0.45 as stored, not 0.44999999999999996 — it then meets
    the 0.45 strong-rumor bar like a slider value would."""
    snap = build_snapshot(["a", "b"], [edge("a", "b", weight=0.5), edge("b", "a", weight=0.5)])
    rumor = deed_rumor("a", support=0.6)
    (hop,) = plan_spread(snap, rumor, origin_region_id="a", reached={"a"}, tuning=PlayTuning())
    assert hop.support == 0.45
