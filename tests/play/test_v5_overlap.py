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
from typing import Any

import pytest

from locus.play import InMemoryPlayRepository
from locus.play.base import SessionClosedError
from locus.play.errors import GmBusyError, SeedAlreadyRunningError
from locus.play.event.suggester import EventSuggester
from locus.play.models import EventCategory, EventStatus, SessionEvent, TimelineKind
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
from tests.play.strategies import WORLD, build_snapshot, edge
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
    fresh = [{r.id for r in res.fresh} for res in out]
    assert all(fresh), out
    lines = _lines(threaded_repo, sid, TimelineKind.REGENERATE)
    last = [set(e.payload["rumor_ids"]) for e in lines][-1]
    assert _canonical(threaded_repo, sid, "r1") == last  # one set: the last one saved
    earlier = (fresh[0] | fresh[1]) - last
    assert earlier and earlier.isdisjoint(_canonical(threaded_repo, sid, "r1"))
    assert first.isdisjoint(_canonical(threaded_repo, sid, "r1"))
    assert set(lines[-1].payload["deactivated"]) == earlier  # it replaced the first's


def test_tp_v5_11_a_generate_beside_a_regenerate_comes_out_in_order(threaded_repo) -> None:
    """Code plan § 1.1 R-03: generate after → the regenerate's set plus the generate's;
    regenerate after → the regenerate's set only."""
    llm = BlockingDrafts(blocked=False)
    gm = _gm(threaded_repo, llm=llm)
    sid = threaded_repo.create_session(WORLD).id
    gm.rumors.generate_rumors(sid, "r1")
    llm.block()
    out: list[Any] = []
    t = threading.Thread(
        target=lambda: out.extend(
            _together(
                lambda: gm.rumors.generate_rumors(sid, "r1"),
                lambda: gm.rumors.regenerate_region(sid, "r1"),
            )
        )
    )
    t.start()
    try:
        assert llm.wait_entered(2)
    finally:
        llm.release()
        t.join(10)
    generated, regenerated = out
    gen_ids = {r.id for r in generated}
    regen_ids = {r.id for r in regenerated.fresh}
    kinds = [
        e.kind
        for e in threaded_repo.list_timeline(sid)
        if e.kind in (TimelineKind.GENERATE.value, TimelineKind.REGENERATE.value)
    ]
    expected = regen_ids | gen_ids if kinds[-1] == TimelineKind.GENERATE.value else regen_ids
    assert _canonical(threaded_repo, sid, "r1") == expected


# --- TP-V5-12 (RE-P05), the rumor side ------------------------------------------- #
def test_tp_v5_12r_a_failed_line_leaves_the_rumors_as_they_were(threaded_repo) -> None:
    gm = _gm(threaded_repo)
    sid = threaded_repo.create_session(WORLD).id
    before = {r.id: r.support for r in gm.rumors.generate_rumors(sid, "r1")}
    rumor_id = next(iter(before))
    with FailingTimeline(
        threaded_repo,
        kinds=[TimelineKind.GENERATE, TimelineKind.REGENERATE, TimelineKind.ADJUST_SUPPORT],
    ):
        with pytest.raises(RuntimeError):
            gm.rumors.generate_rumors(sid, "r2")
        with pytest.raises(RuntimeError):
            gm.rumors.regenerate_region(sid, "r1")
        with pytest.raises(RuntimeError):
            gm.rumors.adjust_support(sid, rumor_id, 0.9)
    after = {r.id: r.support for r in threaded_repo.list_rumors(sid, include_pruned=True)}
    assert after == before  # no r2 rumor, r1 not swapped, the support unchanged
    assert all(r.active for r in threaded_repo.list_rumors(sid, include_pruned=True))
