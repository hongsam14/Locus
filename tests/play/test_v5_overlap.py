"""V5 — GM writes that overlap in one session (FD business-rules TP-V5-1..13, NFR § 2).

Each overlap runs on both stores (``threaded_repo``: in memory, and the SQL adapter on a
SQLite file) unless the NFR § 2.3 table says otherwise. ``InterleaveGate`` makes two
requests both read before either writes; with the section in place the second waits for
the first and the result is the same as running them in order.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

import pytest

from locus.play import InMemoryPlayRepository
from locus.play.base import SessionClosedError
from locus.play.errors import GmBusyError, RumorInactiveError, SeedAlreadyRunningError
from locus.play.event.suggester import EventDraft, EventDraftList, EventSuggester
from locus.play.models import Deed, EventCategory, EventStatus, SessionEvent, TimelineKind
from locus.play.rumor.generator import RumorGenerator
from locus.play.turn.executor import SyncTurnExecutor
from locus.play.wiring import PlayContainer
from locus.shared.config.tuning import PlayTuning
from locus.shared.models import (
    EventSeed,
    Knowledge,
    KnowledgeGraph,
    Provenance,
    ScopeLink,
    ScopeType,
    SourceKind,
    WorldSnapshot,
)
from tests.play.concurrency import BlockingDrafts, FailingTimeline, InterleaveGate
from tests.play.helpers import compose_play
from tests.play.strategies import WORLD, build_snapshot, deed_rumor, edge
from tests.shared.snapshots import StaticSnapshots

_PROV = Provenance(source=SourceKind.INPUT)
SEED = EventSeed(
    id="seed-blight",
    world_id=WORLD,
    region_id="r1",
    title="Blight in the fields",
    category=EventCategory.PLAGUE,
    magnitude=0.5,
    provenance=Provenance(source=SourceKind.INPUT, generated_by="test"),
)


REGIONS = [f"r{i}" for i in range(5)]
_FAILED_LINE = "timeline write failed"  # FailingTimeline's sentence


def _world() -> WorldSnapshot:
    """Five regions, one fact each (rumor sources), r1 and r2 connected, one seed."""
    facts = [
        Knowledge(world_id=WORLD, statement=f"fact of {rid}", title=rid, provenance=_PROV)
        for rid in REGIONS
    ]
    scopes = [
        ScopeLink(world_id=WORLD, knowledge_id=k.id, region_id=rid, scope_type=ScopeType.DIRECT)
        for k, rid in zip(facts, REGIONS, strict=True)
    ]
    world = build_snapshot(
        REGIONS,
        [edge("r1", "r2"), edge("r2", "r1")],
        kg=KnowledgeGraph(world_id=WORLD, knowledge=facts, scopes=scopes),
    )
    return world.model_copy(update={"event_seeds": [SEED]})


def _gm(repo, *, llm=None, tuning: PlayTuning | None = None) -> PlayContainer:
    world = _world()
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


def _generate(gm: PlayContainer, sid: str, region: str) -> Callable[[], Any]:
    return lambda: gm.rumors.generate_rumors(sid, region)


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
    with InterleaveGate(threaded_repo, "list_region_distortions") as gate:
        out = _together(
            lambda: gm.events.resolve_event(sid, first),
            lambda: gm.events.resolve_event(sid, second),
        )
    assert all(EventStatus(e.status) is EventStatus.RESOLVED for e in out), out
    assert threaded_repo.get_region_distortion(sid, "r1") == pytest.approx(0.3)
    assert len(_lines(threaded_repo, sid, TimelineKind.EVENT_RESOLVED)) == 2
    assert not gate.met  # the section put the second read after the first write (#23)


def test_tp_v5_1_one_event_resolved_twice_at_once_restores_once(threaded_repo) -> None:
    """BR-V5-05 (code review 01 #3): a double click — both read it ACTIVE outside; the
    second finds it resolved in the section and gives it back with no line."""
    gm = _gm(threaded_repo)
    sid = threaded_repo.create_session(WORLD).id
    threaded_repo.set_region_distortion(sid, "r1", 0.45)
    eid = _active_event(threaded_repo, sid, "r1", {"r1": 0.15})
    with InterleaveGate(threaded_repo, "get_event") as gate:  # both read it as ACTIVE
        out = _together(
            lambda: gm.events.resolve_event(sid, eid), lambda: gm.events.resolve_event(sid, eid)
        )
    assert gate.met and all(isinstance(o, SessionEvent) for o in out), out
    assert threaded_repo.get_region_distortion(sid, "r1") == pytest.approx(0.3)
    assert len(_lines(threaded_repo, sid, TimelineKind.EVENT_RESOLVED)) == 1


def test_a_resolve_restores_from_the_event_as_it_is_in_the_section(threaded_repo) -> None:
    """U3 review #10 kept by V5 (code review 01 #17): a GM set between the resolve's
    first read and its section cleared r1's contribution, so r1 keeps the GM's value."""
    gm = _gm(threaded_repo)
    sid = threaded_repo.create_session(WORLD).id
    threaded_repo.set_region_distortion(sid, "r1", 0.45)
    eid = _active_event(threaded_repo, sid, "r1", {"r1": 0.15})
    undo = _after_first_read(
        threaded_repo, lambda: gm.distortions.set_region_distortion(sid, "r1", 0.7)
    )
    try:
        gm.events.resolve_event(sid, eid)
    finally:
        undo()
    assert threaded_repo.get_region_distortion(sid, "r1") == pytest.approx(0.7)


# --- TP-V5-2 (#12): one seed start wins ---------------------------------------- #
def test_tp_v5_2_two_starts_of_one_seed_make_one_event(threaded_repo) -> None:
    gm = _gm(threaded_repo)
    sid = threaded_repo.create_session(WORLD).id
    with InterleaveGate(threaded_repo, "list_events") as gate:  # after "is it running?"
        out = _together(lambda: gm.seeds.start(sid, SEED.id), lambda: gm.seeds.start(sid, SEED.id))
    assert not gate.met  # the check sits in the section now
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
    with InterleaveGate(threaded_repo, "get_event") as gate:  # both read a suggestion
        out = _together(
            lambda: gm.events.approve_event(sid, eid), lambda: gm.events.approve_event(sid, eid)
        )
    assert gate.met and all(isinstance(o, SessionEvent) for o in out), out
    assert EventStatus(threaded_repo.get_event(sid, eid).status) is EventStatus.ACTIVE
    assert len(threaded_repo.list_events(sid, EventStatus.ACTIVE.value)) == 1
    assert len(_lines(threaded_repo, sid, TimelineKind.EVENT_APPROVED)) == 1


def _after_first_read(
    repo, then: Callable[[], Any], method: str = "get_event"
) -> Callable[[], None]:
    """After the next ``method`` call returns, run ``then`` — the other write finishing
    between this write's first read and its section. Returns the undo."""
    original = getattr(repo, method)
    fired: list[bool] = []

    def read(*a: Any, **kw: Any) -> Any:
        result = original(*a, **kw)
        if not fired:
            fired.append(True)
            then()
        return result

    setattr(repo, method, read)
    return lambda: vars(repo).pop(method, None)


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


def test_tp_v5_9_approved_and_resolved_meanwhile_the_approve_is_refused(threaded_repo) -> None:
    """BR-V5-07 (code review 01 #16): resolved → 400, never ACTIVE again, no second line."""
    gm = _gm(threaded_repo)
    sid = threaded_repo.create_session(WORLD).id
    eid = _suggested(gm, sid)

    def approve_then_resolve() -> None:
        gm.events.approve_event(sid, eid)
        gm.events.resolve_event(sid, eid)

    undo = _after_first_read(threaded_repo, approve_then_resolve)
    try:
        with pytest.raises(ValueError):  # 400
            gm.events.approve_event(sid, eid)
    finally:
        undo()
    assert EventStatus(threaded_repo.get_event(sid, eid).status) is EventStatus.RESOLVED
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
    ) as failing:
        with pytest.raises(RuntimeError, match=_FAILED_LINE):
            gm.events.create_event(sid, "r1", category=EventCategory.WAR, magnitude=0.4)
        with pytest.raises(RuntimeError, match=_FAILED_LINE):
            gm.events.approve_event(sid, pending)
        with pytest.raises(RuntimeError, match=_FAILED_LINE):
            gm.events.suggest_events(sid)
        with pytest.raises(RuntimeError, match=_FAILED_LINE):
            gm.seeds.start(sid, SEED.id)
    assert failing.raised == 4  # each failed on its line, not on something else (#20)
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


def test_tp_v5_13_a_seed_start_is_one_section_and_reads_the_world_before_it(
    threaded_repo,
) -> None:
    """BR-V5-04/06 (code review 01 #7): the check and the create share one section; the
    world (a graph round trip behind the cache) is read before it, never inside."""
    gm = _gm(threaded_repo, tuning=PlayTuning(gm_write_wait_s=0.1))
    sid = threaded_repo.create_session(WORLD).id
    inside: list[bool] = []
    reads_inside: list[bool] = []
    real_open = gm.events.section.open
    snapshots = gm.events._snapshots
    real_get = snapshots.get

    @contextmanager
    def watched(session_id: str):
        with real_open(session_id) as pair:
            inside.append(True)
            try:
                yield pair
            finally:
                inside.pop()

    gm.events.section.open = watched
    snapshots.get = lambda world_id: (reads_inside.append(bool(inside)), real_get(world_id))[1]
    try:
        event = gm.seeds.start(sid, SEED.id)
    finally:
        del gm.events.section.open
        del snapshots.get
    assert EventStatus(event.status) is EventStatus.ACTIVE
    assert len(_lines(threaded_repo, sid, TimelineKind.EVENT_CREATED)) == 1
    assert reads_inside and not any(reads_inside)


def test_the_sections_share_the_container_guard() -> None:
    """Wiring (code plan R-03, code review 01 #2): every GM write and the close use the
    one guard of the container."""
    gm = _gm(InMemoryPlayRepository())
    for service in (gm.events, gm.rumors, gm.deeds, gm.distortions):
        assert service.section.guard is gm.guard
    assert gm.sessions._guard is gm.guard and gm.turns.guard is gm.guard


def test_every_gm_save_waits_on_the_container_s_short_write(threaded_repo) -> None:
    """The same, by behaviour: while the container's short write is held, each write
    gives up after the wait with 409 gm_busy and saves nothing (code review 01 #2)."""
    gm = _gm(threaded_repo, tuning=PlayTuning(gm_write_wait_s=0.05))
    sid = threaded_repo.create_session(WORLD).id
    deed_id, rumor_id = _deed_with_rumor(threaded_repo, sid)
    lines = len(threaded_repo.list_timeline(sid))
    held = threading.Event()
    done = threading.Event()

    def hold() -> None:
        with gm.guard.short_write(sid, timeout_s=1):
            held.set()
            done.wait(5)

    t = threading.Thread(target=hold)
    t.start()
    try:
        assert held.wait(5)
        writes = [
            lambda: gm.events.create_event(sid, "r1", category=EventCategory.WAR, magnitude=0.4),
            lambda: gm.rumors.generate_rumors(sid, "r1"),
            lambda: gm.rumors.adjust_support(sid, rumor_id, 0.9),
            lambda: gm.deeds.void(sid, deed_id),
            lambda: gm.distortions.set_region_distortion(sid, "r1", 0.6),
            lambda: gm.seeds.start(sid, SEED.id),
            lambda: gm.sessions.close_session(sid),
        ]
        for write in writes:
            with pytest.raises(GmBusyError):
                write()
    finally:
        done.set()
        t.join(5)
    assert len(threaded_repo.list_timeline(sid)) == lines
    assert threaded_repo.get_session(sid).status == "open"


def test_a_section_takes_the_short_write_before_its_unit_of_work() -> None:
    """BR-V5-04 lock order (code review 01 #21): lease → short write → unit of work."""
    repo = InMemoryPlayRepository()
    gm = _gm(repo)
    sid = repo.create_session(WORLD).id
    order: list[str] = []
    real_write, real_uow = gm.guard.short_write, repo.uow

    @contextmanager
    def short_write(session_id: str, *, timeout_s: float):
        order.append("short write")
        with real_write(session_id, timeout_s=timeout_s):
            yield

    def uow():
        order.append("unit of work")
        return real_uow()

    gm.guard.short_write = short_write
    repo.uow = uow
    try:
        gm.events.create_event(sid, "r1", category=EventCategory.WAR, magnitude=0.4)
    finally:
        del gm.guard.short_write
        del repo.uow
    assert order == ["short write", "unit of work"]


def test_a_suggestion_that_matches_no_region_still_says_the_session_closed() -> None:
    """BLM § 2 (code review 01 #8): closed during the LLM call → 409 even with nothing
    to save."""
    repo = InMemoryPlayRepository()
    sid = repo.create_session(WORLD).id

    class ClosesMeanwhile:
        def structured(self, prompt, schema, *, system=None):
            repo.close_session(sid)  # a close or a world replace during the call
            return EventDraftList(
                drafts=[EventDraft(region_id="nowhere", category=EventCategory.WAR, magnitude=0.5)]
            )

        def complete(self, prompt, *, system=None):  # pragma: no cover
            return ""

    gm = compose_play(
        repo,
        RumorGenerator(ClosesMeanwhile()),
        StaticSnapshots(_world()),
        suggester=EventSuggester(ClosesMeanwhile()),
        executor=SyncTurnExecutor(),
    )
    with pytest.raises(SessionClosedError):
        gm.events.suggest_events(sid)
    assert repo.list_events(sid) == []


# --- TP-V5-4 (RE-P02): a close while the drafts are made ------------------------ #
def test_tp_v5_4_a_close_during_a_generate_ends_at_once_and_the_generate_saves_nothing(
    threaded_repo,
) -> None:
    llm = BlockingDrafts()
    gm = _gm(threaded_repo, llm=llm)
    sid = threaded_repo.create_session(WORLD).id
    result: list[Any] = []
    t = threading.Thread(target=lambda: result.extend(_together(_generate(gm, sid, "r1"))))
    t.start()
    try:
        assert llm.wait_entered(1)
        began = time.monotonic()
        gm.sessions.close_session(sid)  # waits for no draft (BR-V5-15)
        assert time.monotonic() - began < 1.0
    finally:
        llm.release()
        t.join(5)
    assert not t.is_alive() and len(result) == 1
    assert isinstance(result[0], SessionClosedError), result
    assert threaded_repo.list_rumors(sid, include_pruned=True) == []
    assert _lines(threaded_repo, sid, TimelineKind.GENERATE) == []
    assert len(_lines(threaded_repo, sid, TimelineKind.SESSION_CLOSED)) == 1


# --- TP-V5-7 (BR-V5-13): a bulk generate of five ---------------------------------- #
def test_tp_v5_7_five_generates_draft_together_and_all_save(threaded_repo) -> None:
    llm = BlockingDrafts()
    gm = _gm(threaded_repo, llm=llm)
    sid = threaded_repo.create_session(WORLD).id
    out: list[Any] = []
    t = threading.Thread(
        target=lambda: out.extend(_together(*(_generate(gm, sid, rid) for rid in REGIONS)))
    )
    t.start()
    try:
        together = llm.wait_entered(len(REGIONS))  # every draft outside the section
    finally:
        llm.release()
        t.join(10)
    assert not t.is_alive() and len(out) == len(REGIONS)
    assert together and llm.max_inside >= 2
    assert all(isinstance(o, list) and o for o in out), out  # no 409, every region drafted
    regions = {r.region_id for r in threaded_repo.list_rumors(sid)}
    assert regions == set(REGIONS)
    assert len(_lines(threaded_repo, sid, TimelineKind.GENERATE)) == len(REGIONS)


# --- TP-V5-11 (RE-P07): regenerates that overlap ---------------------------------- #
def _canonical(repo, sid: str, region: str) -> set[str]:
    return {
        r.id
        for r in repo.list_rumors(sid, region)
        if r.origin_kind == "canonical" and not r.promoted
    }


def test_tp_v5_11_of_two_regenerates_the_last_one_s_set_stays(threaded_repo) -> None:
    llm = BlockingDrafts(blocked=False)
    gm = _gm(threaded_repo, llm=llm)
    sid = threaded_repo.create_session(WORLD).id
    first = {r.id for r in gm.rumors.generate_rumors(sid, "r1")}
    llm.block()
    out: list[Any] = []
    t = threading.Thread(
        target=lambda: out.extend(
            _together(
                lambda: gm.rumors.regenerate_region(sid, "r1"),
                lambda: gm.rumors.regenerate_region(sid, "r1"),
            )
        )
    )
    t.start()
    try:
        assert llm.wait_entered(2)  # both draft before either saves
    finally:
        llm.release()
        t.join(10)
    assert not t.is_alive() and len(out) == 2
    fresh = [{r.id for r in res.fresh} for res in out]
    assert all(fresh), out
    lines = _lines(threaded_repo, sid, TimelineKind.REGENERATE)
    last = [set(e.payload["rumor_ids"]) for e in lines][-1]
    assert _canonical(threaded_repo, sid, "r1") == last  # one set: the last one saved
    earlier = (fresh[0] | fresh[1]) - last
    assert earlier and earlier.isdisjoint(_canonical(threaded_repo, sid, "r1"))
    assert first.isdisjoint(_canonical(threaded_repo, sid, "r1"))
    assert set(lines[-1].payload["deactivated"]) == earlier  # it replaced the first's


@pytest.mark.parametrize("last", ["regenerate", "generate"])
def test_tp_v5_11_a_generate_beside_a_regenerate_comes_out_in_order(
    threaded_repo, last: str
) -> None:
    """Code plan § 1.1 R-03: the other write finishes while this one drafts (a fixed
    order, code review 01 #19). Regenerate saves last → its set only; generate saves
    last → the regenerate's set plus the generate's."""
    llm = BlockingDrafts(blocked=False)
    gm = _gm(threaded_repo, llm=llm)
    sid = threaded_repo.create_session(WORLD).id
    before = {r.id for r in gm.rumors.generate_rumors(sid, "r1")}
    done: dict[str, Any] = {}
    if last == "regenerate":
        llm.on_first = lambda: done.update(gen=gm.rumors.generate_rumors(sid, "r1"))
        done["regen"] = gm.rumors.regenerate_region(sid, "r1")
    else:
        llm.on_first = lambda: done.update(regen=gm.rumors.regenerate_region(sid, "r1"))
        done["gen"] = gm.rumors.generate_rumors(sid, "r1")
    gen_ids = {r.id for r in done["gen"]}
    regen_ids = {r.id for r in done["regen"].fresh}
    assert gen_ids and regen_ids
    expected = regen_ids if last == "regenerate" else regen_ids | gen_ids
    assert _canonical(threaded_repo, sid, "r1") == expected
    assert before.isdisjoint(_canonical(threaded_repo, sid, "r1"))


# --- TP-V5-12 (RE-P05), the rumor side ------------------------------------------- #
def test_tp_v5_12r_a_failed_line_leaves_the_rumors_as_they_were(threaded_repo) -> None:
    gm = _gm(threaded_repo)
    sid = threaded_repo.create_session(WORLD).id
    before = {r.id: r.support for r in gm.rumors.generate_rumors(sid, "r1")}
    rumor_id = next(iter(before))
    with FailingTimeline(
        threaded_repo,
        kinds=[TimelineKind.GENERATE, TimelineKind.REGENERATE, TimelineKind.ADJUST_SUPPORT],
    ) as failing:
        with pytest.raises(RuntimeError, match=_FAILED_LINE):
            gm.rumors.generate_rumors(sid, "r2")
        with pytest.raises(RuntimeError, match=_FAILED_LINE):
            gm.rumors.regenerate_region(sid, "r1")
        with pytest.raises(RuntimeError, match=_FAILED_LINE):
            gm.rumors.adjust_support(sid, rumor_id, 0.9)
    assert failing.raised == 3
    after = {r.id: r.support for r in threaded_repo.list_rumors(sid, include_pruned=True)}
    assert after == before  # no r2 rumor, r1 not swapped, the support unchanged
    assert all(r.active for r in threaded_repo.list_rumors(sid, include_pruned=True))


# --- TP-V5-3 (RE-P01): a support change against a void -------------------------- #
def _deed_with_rumor(repo, sid: str) -> tuple[str, str]:
    deed = repo.record_deed(
        Deed(
            session_id=sid,
            player_id="p",
            region_id="r1",
            kind="arrival",
            text="Ari came.",
            witnessed_npc_ids=["n1"],
        )
    )
    rumor = deed_rumor("r1", deed_id=deed.id, support=0.6).model_copy(update={"session_id": sid})
    repo.upsert_rumor(rumor)
    return deed.id, rumor.id


def test_tp_v5_3_a_support_change_after_a_void_is_refused_and_nothing_spreads(
    threaded_repo,
) -> None:
    gm = _gm(threaded_repo)
    sid = threaded_repo.create_session(WORLD).id
    deed_id, rumor_id = _deed_with_rumor(threaded_repo, sid)
    undo = _after_first_read(threaded_repo, lambda: gm.deeds.void(sid, deed_id), method="get_rumor")
    try:
        with pytest.raises(RumorInactiveError):  # 409 rumor_inactive (Q2=A)
            gm.rumors.adjust_support(sid, rumor_id, 0.9)
    finally:
        undo()
    rumor = threaded_repo.get_rumor(sid, rumor_id)
    assert rumor is not None and not rumor.active and rumor.support == 0.6
    assert _lines(threaded_repo, sid, TimelineKind.ADJUST_SUPPORT) == []
    assert len(_lines(threaded_repo, sid, TimelineKind.DEED_VOIDED)) == 1
    gm.turns.advance(sid)  # a revived rumor would hop r1 -> r2 here
    family = threaded_repo.list_rumors_by_origin(sid, deed_id=deed_id, include_inactive=True)
    assert [r.id for r in family] == [rumor_id]


def test_tp_v5_3_two_voids_that_overlap_write_one_line(threaded_repo) -> None:
    gm = _gm(threaded_repo)
    sid = threaded_repo.create_session(WORLD).id
    deed_id, rumor_id = _deed_with_rumor(threaded_repo, sid)
    with InterleaveGate(threaded_repo, "get_deed") as gate:  # both read it as not voided
        out = _together(lambda: gm.deeds.void(sid, deed_id), lambda: gm.deeds.void(sid, deed_id))
    assert gate.met
    assert sorted(len(o.deactivated_rumor_ids) for o in out) == [0, 1], out
    assert threaded_repo.get_deed(sid, deed_id).voided
    assert len(_lines(threaded_repo, sid, TimelineKind.DEED_VOIDED)) == 1


# --- TP-V5-10 (U8 § 3): the feedback share is recorded once ---------------------- #
def test_tp_v5_10_two_sets_of_one_region_record_the_share_once(threaded_repo) -> None:
    gm = _gm(threaded_repo)
    sid = threaded_repo.create_session(WORLD).id
    threaded_repo.set_region_distortion(sid, "r1", 0.5, feedback_share=0.2)
    with InterleaveGate(threaded_repo, "list_region_distortions") as gate:  # after the read
        out = _together(
            lambda: gm.distortions.set_region_distortion(sid, "r1", 0.4),
            lambda: gm.distortions.set_region_distortion(sid, "r1", 0.6),
        )
    shares = sorted(
        e.payload["feedback_share_cleared"]
        for e in _lines(threaded_repo, sid, TimelineKind.SET_DISTORTION)
    )
    assert shares == [0.0, 0.2] and not gate.met
    for row, degree in zip(out, (0.4, 0.6), strict=True):  # each gets the row it saved
        assert row.region_id == "r1" and row.feedback_share == 0.0
        assert row.distortion_degree == degree
    assert threaded_repo.get_region_distortion(sid, "r1") in (0.4, 0.6)  # the later one
