"""V5 — GM writes that overlap in one session (FD business-rules TP-V5-1..13, NFR § 2).

Each overlap runs on both stores (``threaded_repo``: in memory, and the SQL adapter on a
SQLite file) unless the NFR § 2.3 table says otherwise. ``InterleaveGate`` makes two
requests both read before either writes; with the section in place the second waits for
the first and the result is the same as running them in order.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

import pytest

from locus.play import InMemoryPlayRepository
from locus.play.errors import GmBusyError, SeedAlreadyRunningError
from locus.play.event.suggester import EventSuggester
from locus.play.models import EventCategory, EventStatus, SessionEvent, TimelineKind
from locus.play.rumor.generator import RumorGenerator
from locus.play.turn.executor import SyncTurnExecutor
from locus.play.wiring import PlayContainer
from locus.shared.config.tuning import PlayTuning
from locus.shared.models import EventSeed, Provenance, SourceKind
from tests.play.concurrency import BlockingDrafts, FailingTimeline, InterleaveGate
from tests.play.helpers import compose_play
from tests.play.strategies import WORLD, build_snapshot, edge
from tests.shared.snapshots import StaticSnapshots

SEED = EventSeed(
    id="seed-blight",
    world_id=WORLD,
    region_id="r1",
    title="Blight in the fields",
    category=EventCategory.PLAGUE,
    magnitude=0.5,
    provenance=Provenance(source=SourceKind.INPUT, generated_by="test"),
)


def _gm(repo, *, llm=None, tuning: PlayTuning | None = None) -> PlayContainer:
    world = build_snapshot(["r1", "r2"], [edge("r1", "r2"), edge("r2", "r1")])
    world = world.model_copy(update={"event_seeds": [SEED]})
    llm = llm or BlockingDrafts(blocked=False)
    extra: dict[str, Any] = {"tuning": tuning} if tuning is not None else {}
    return compose_play(
        repo,
        RumorGenerator(llm),
        StaticSnapshots(world),
        suggester=EventSuggester(llm),
        executor=SyncTurnExecutor(),
        **extra,
    )


def _together(*calls: Callable[[], Any]) -> list[Any]:
    """Run each call in its own thread, started together; each result or raised error."""
    start = threading.Barrier(len(calls))
    out: list[Any] = [None] * len(calls)

    def run(i: int) -> None:
        start.wait()
        try:
            out[i] = calls[i]()
        except Exception as exc:  # noqa: BLE001 - the outcome is what the test checks
            out[i] = exc

    threads = [threading.Thread(target=run, args=(i,)) for i in range(len(calls))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert not any(t.is_alive() for t in threads)
    return out


def _lines(repo, sid: str, kind: TimelineKind) -> list:
    return [e for e in repo.list_timeline(sid) if e.kind == kind.value]


def _active_event(repo, sid: str, region: str, contributions: dict[str, float]) -> str:
    event = SessionEvent(
        session_id=sid,
        region_id=region,
        category=EventCategory.WAR,
        magnitude=0.5,
        status=EventStatus.ACTIVE,
        created_turn=0,
        contributions=contributions,
        provenance=Provenance(source=SourceKind.SIMULATION, generated_by="gm:event"),
    )
    return repo.create_event(event).id


# --- TP-V5-1 (#9): two resolves restore both ------------------------------------ #
def test_tp_v5_1_two_resolves_that_overlap_restore_both(threaded_repo) -> None:
    """NFR § 2.3: the in-memory unit of work already holds the store lock, so the
    overlap shows only on SQL; in memory this checks the result."""
    gm = _gm(threaded_repo)
    sid = threaded_repo.create_session(WORLD).id
    threaded_repo.set_region_distortion(sid, "r1", 0.51)  # 0.3 + 0.15 + 0.06
    first = _active_event(threaded_repo, sid, "r1", {"r1": 0.15})
    second = _active_event(threaded_repo, sid, "r1", {"r1": 0.06})
    with InterleaveGate(threaded_repo, "list_region_distortions"):
        out = _together(
            lambda: gm.events.resolve_event(sid, first),
            lambda: gm.events.resolve_event(sid, second),
        )
    assert all(EventStatus(e.status) is EventStatus.RESOLVED for e in out), out
    degrees = {d.region_id: d.distortion_degree for d in threaded_repo.list_region_distortions(sid)}
    assert degrees["r1"] == pytest.approx(0.3)
    assert len(_lines(threaded_repo, sid, TimelineKind.EVENT_RESOLVED)) == 2


# --- TP-V5-2 (#12): one seed start wins ---------------------------------------- #
def test_tp_v5_2_two_starts_of_one_seed_make_one_event(threaded_repo) -> None:
    gm = _gm(threaded_repo)
    sid = threaded_repo.create_session(WORLD).id
    with InterleaveGate(threaded_repo, "list_events"):  # right after "is it running?"
        out = _together(lambda: gm.seeds.start(sid, SEED.id), lambda: gm.seeds.start(sid, SEED.id))
    started = [o for o in out if isinstance(o, SessionEvent)]
    refused = [o for o in out if isinstance(o, SeedAlreadyRunningError)]
    assert len(started) == 1 and len(refused) == 1, out
    active = threaded_repo.list_events(sid, EventStatus.ACTIVE.value)
    assert [e.id for e in active] == [started[0].id]
    assert len(_lines(threaded_repo, sid, TimelineKind.EVENT_CREATED)) == 1


# --- TP-V5-9 (RE-P06): approve twice, approve against discard -------------------- #
def _suggested(gm: PlayContainer, sid: str) -> str:
    (event,) = gm.events.suggest_events(sid)
    return event.id


def test_tp_v5_9_two_approves_that_overlap_write_one_line(threaded_repo) -> None:
    gm = _gm(threaded_repo)
    sid = threaded_repo.create_session(WORLD).id
    eid = _suggested(gm, sid)
    with InterleaveGate(threaded_repo, "get_event"):  # both read it as a suggestion
        out = _together(
            lambda: gm.events.approve_event(sid, eid), lambda: gm.events.approve_event(sid, eid)
        )
    assert all(isinstance(o, SessionEvent) for o in out), out
    assert EventStatus(threaded_repo.get_event(sid, eid).status) is EventStatus.ACTIVE
    assert len(threaded_repo.list_events(sid, EventStatus.ACTIVE.value)) == 1
    assert len(_lines(threaded_repo, sid, TimelineKind.EVENT_APPROVED)) == 1


def _after_first_read(repo, then: Callable[[], Any]) -> Callable[[], None]:
    """After the next ``get_event`` returns, run ``then`` — the other write finishing
    between this write's first read and its section. Returns the undo."""
    original = repo.get_event
    fired: list[bool] = []

    def get_event(*a: Any, **kw: Any) -> Any:
        result = original(*a, **kw)
        if not fired:
            fired.append(True)
            then()
        return result

    repo.get_event = get_event
    return lambda: vars(repo).pop("get_event", None)


def test_tp_v5_9_approve_first_then_the_discard_is_refused(threaded_repo) -> None:
    gm = _gm(threaded_repo)
    sid = threaded_repo.create_session(WORLD).id
    eid = _suggested(gm, sid)
    undo = _after_first_read(threaded_repo, lambda: gm.events.approve_event(sid, eid))
    try:
        with pytest.raises(ValueError):  # 400: no longer a suggestion
            gm.events.discard_event(sid, eid)
    finally:
        undo()
    assert EventStatus(threaded_repo.get_event(sid, eid).status) is EventStatus.ACTIVE
    assert _lines(threaded_repo, sid, TimelineKind.EVENT_DISCARDED) == []
    assert len(_lines(threaded_repo, sid, TimelineKind.EVENT_APPROVED)) == 1


def test_tp_v5_9_discard_first_then_the_approve_finds_nothing(threaded_repo) -> None:
    gm = _gm(threaded_repo)
    sid = threaded_repo.create_session(WORLD).id
    eid = _suggested(gm, sid)
    undo = _after_first_read(threaded_repo, lambda: gm.events.discard_event(sid, eid))
    try:
        with pytest.raises(LookupError):  # 404
            gm.events.approve_event(sid, eid)
    finally:
        undo()
    assert threaded_repo.get_event(sid, eid) is None
    assert _lines(threaded_repo, sid, TimelineKind.EVENT_APPROVED) == []
    assert len(_lines(threaded_repo, sid, TimelineKind.EVENT_DISCARDED)) == 1


# --- TP-V5-12 (RE-P05), the event side: no row without its line ------------------ #
def test_tp_v5_12e_a_failed_line_leaves_no_event_row(threaded_repo) -> None:
    gm = _gm(threaded_repo)
    sid = threaded_repo.create_session(WORLD).id
    pending = _suggested(gm, sid)
    with FailingTimeline(
        threaded_repo,
        kinds=[
            TimelineKind.EVENT_CREATED,
            TimelineKind.EVENT_APPROVED,
            TimelineKind.EVENT_SUGGESTED,
        ],
    ):
        with pytest.raises(RuntimeError):
            gm.events.create_event(sid, "r1", category=EventCategory.WAR, magnitude=0.4)
        with pytest.raises(RuntimeError):
            gm.events.approve_event(sid, pending)
        with pytest.raises(RuntimeError):
            gm.events.suggest_events(sid)
        with pytest.raises(RuntimeError):
            gm.seeds.start(sid, SEED.id)
    events = threaded_repo.list_events(sid)
    assert [e.id for e in events] == [pending]  # nothing created by the four
    assert EventStatus(events[0].status) is EventStatus.SUGGESTED  # the approve rolled back
    assert gm.seeds.list_seeds(sid)[0].running_event_id is None


# --- TP-V5-13: the wait cap and the seed's re-entry ------------------------------ #
def test_tp_v5_13_a_write_past_the_wait_is_refused_and_writes_nothing(threaded_repo) -> None:
    gm = _gm(threaded_repo, tuning=PlayTuning(gm_write_wait_s=0.1))
    sid = threaded_repo.create_session(WORLD).id
    held = threading.Event()
    done = threading.Event()

    def hold() -> None:  # a save section that does not end
        with gm.guard.short_write(sid, timeout_s=1):
            held.set()
            done.wait(5)

    t = threading.Thread(target=hold)
    t.start()
    try:
        assert held.wait(5)
        with pytest.raises(GmBusyError):
            gm.events.create_event(sid, "r1", category=EventCategory.WAR, magnitude=0.4)
        with pytest.raises(GmBusyError):
            gm.seeds.start(sid, SEED.id)
    finally:
        done.set()
        t.join(5)
    assert threaded_repo.list_events(sid) == [] and threaded_repo.list_timeline(sid) == []


def test_tp_v5_13_a_seed_start_enters_its_section_again_without_a_deadlock(
    threaded_repo,
) -> None:
    gm = _gm(threaded_repo, tuning=PlayTuning(gm_write_wait_s=0.1))
    sid = threaded_repo.create_session(WORLD).id
    event = gm.seeds.start(sid, SEED.id)  # lock → create_event's section (BR-V5-04)
    assert EventStatus(event.status) is EventStatus.ACTIVE
    assert len(_lines(threaded_repo, sid, TimelineKind.EVENT_CREATED)) == 1


def test_the_sections_share_the_container_guard() -> None:
    """Wiring (code plan R-03): the event service and the seeds use the shared guard."""
    gm = _gm(InMemoryPlayRepository())
    assert gm.events.section.guard is gm.guard
