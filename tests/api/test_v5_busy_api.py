"""V5 — a busy session over HTTP: the player's 409 codes and the busy flags (TP-V5-8), the
close/turn gap (TP-V5-14) and a world replace beside a GM write (TP-V5-15, part 1; the GM
generate during a replace is in Step 5.2, code plan R-04)."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager

from fastapi.testclient import TestClient

from api.errors import ERROR_CODES
from api.main import create_app
from locus.play.errors import GmBusyError, TurnInProgressError
from locus.play.models import TimelineKind
from locus.play.wiring import PlayContainer
from locus.shared.config.tuning import PlayTuning
from tests.api.play_fixtures import play_container
from tests.api.test_world_api import _client as world_client
from tests.api.test_world_api import _file


def _app(**kw) -> tuple[PlayContainer, TestClient]:
    p = play_container(**kw)
    return p, TestClient(create_app(play=p))


def _start(client: TestClient) -> str:
    r = client.post("/api/play/worlds/w/sessions", json={"name": "Ari", "start_region_id": "r1"})
    assert r.status_code == 201, r.text
    return r.json()["session"]["id"]


def _act(client: TestClient, sid: str):
    return client.post(f"/api/play/sessions/{sid}/act", json={"type": "wait"})


def _clean(body: dict, *internals: str) -> None:
    """FR-C5: a 409 sentence names no session id, run id or lease token."""
    detail = str(body["detail"])
    for needle in internals:
        assert needle not in detail
    assert "gm:" not in detail and "editor:" not in detail


def _closed_lines(p: PlayContainer, sid: str) -> int:
    return sum(e.kind == TimelineKind.SESSION_CLOSED.value for e in p.repo.list_timeline(sid))


@contextmanager
def _close_waits_on_its_section(
    p: PlayContainer, sid: str, closes: int = 1
) -> Iterator[Callable[[], list[int]]]:
    """Hold the session's short write, start ``closes`` closes and return once each has
    marked the session closing and is waiting for the section. On exit the section is
    let go and the closes finish; the yielded callable returns their status codes."""
    client = TestClient(create_app(play=p))
    original = p.guard.short_write
    waiting = threading.Semaphore(0)

    def short_write(session_id: str, *, timeout_s: float) -> AbstractContextManager[None]:
        waiting.release()  # only closes run here: one is inside `closing`, about to wait
        return original(session_id, timeout_s=timeout_s)

    codes: list[int] = []
    lock = threading.Lock()

    def close() -> None:
        r = client.post(f"/api/play/sessions/{sid}/close")
        with lock:
            codes.append(r.status_code)

    p.guard.short_write = short_write  # type: ignore[method-assign]
    threads = [threading.Thread(target=close) for _ in range(closes)]
    try:
        with original(sid, timeout_s=1):
            for t in threads:
                t.start()
            for _ in threads:
                assert waiting.acquire(timeout=5)
            yield lambda: codes
    finally:
        for t in threads:
            t.join(timeout=5)
        p.guard.short_write = original  # type: ignore[method-assign]


# --- TP-V5-8 ----------------------------------------------------------------- #
def test_tp_v5_8_a_player_action_says_turn_gm_or_closing_and_names_nothing_inside() -> None:
    p, client = _app()
    sid = _start(client)

    with p.guard.hold(sid) as token:  # a GM write in progress
        busy = _act(client, sid)
        view = client.get(f"/api/play/sessions/{sid}/region").json()
    assert busy.status_code == 409 and busy.json()["code"] == "gm_busy"
    _clean(busy.json(), sid, token)
    assert view["gm_busy"] is True and view["turn_running"] is False  # BR-V5-22

    p.guard.acquire(sid, "run-secret")
    try:
        turn = _act(client, sid)
        view = client.get(f"/api/play/sessions/{sid}/region").json()
    finally:
        p.guard.release(sid)
    assert turn.status_code == 409 and turn.json()["code"] == "turn_running"
    _clean(turn.json(), sid, "run-secret")
    assert view["turn_running"] is True and view["gm_busy"] is False

    with p.guard.closing(sid):  # a close under way
        closing = _act(client, sid)
    assert closing.status_code == 409 and closing.json()["code"] == "session_closed"
    _clean(closing.json(), sid)

    view = client.get(f"/api/play/sessions/{sid}/region").json()
    assert view["turn_running"] is False and view["gm_busy"] is False
    assert _act(client, sid).status_code == 202  # nothing left holding it
    assert p.repo.get_session(sid).status == "open"  # the probes closed nothing


def test_tp_v5_8_gm_busy_is_matched_before_its_parent() -> None:
    """BR-V5-24: the table's first match wins, so the subclass row comes first."""
    order = [exc for exc, _status, _code in ERROR_CODES]
    assert order.index(GmBusyError) < order.index(TurnInProgressError)
    assert {exc: code for exc, _s, code in ERROR_CODES}[GmBusyError] == "gm_busy"


# --- TP-V5-14 ---------------------------------------------------------------- #
def test_tp_v5_14_a_turn_started_while_a_close_waits_is_refused_as_closed() -> None:
    p, client = _app()
    sid = _start(client)
    with _close_waits_on_its_section(p, sid) as codes:
        r = _act(client, sid)  # the close has marked the session but not yet closed it
        assert r.status_code == 409 and r.json()["code"] == "session_closed"
        assert p.repo.get_session(sid).status == "open"
    assert codes() == [200]
    assert p.repo.get_session(sid).status == "closed"
    assert _closed_lines(p, sid) == 1
    assert p.repo.list_runs(sid) == []  # the refused turn left no run
    assert sid not in p.guard._writes  # its short-write lock is dropped (review 01 #10)
    closed = _act(client, sid)  # and once closed: still no session id (code review 01 #6)
    assert closed.status_code == 409 and closed.json()["code"] == "session_closed"
    _clean(closed.json(), sid)


def test_tp_v5_14_two_overlapping_closes_keep_turns_out_and_write_one_line() -> None:
    p, client = _app()
    sid = _start(client)
    with _close_waits_on_its_section(p, sid, closes=2) as codes:
        assert _act(client, sid).json()["code"] == "session_closed"
    assert sorted(codes()) == [200, 200]  # idempotent (BR-S1-4)
    assert _closed_lines(p, sid) == 1  # written once (code plan R-01)
    assert _act(client, sid).json()["code"] == "session_closed"


def test_tp_v5_14_a_close_past_the_wait_answers_gm_busy_and_lifts_its_hold() -> None:
    """BR-V5-03: a save section that outlasts the wait refuses the close; the close's
    hold on new turns goes with it."""
    p, client = _app(tuning=PlayTuning(gm_write_wait_s=0.05))
    sid = _start(client)
    result: list = []
    with p.guard.short_write(sid, timeout_s=1):  # a GM save section that will not end
        t = threading.Thread(
            target=lambda: result.append(client.post(f"/api/play/sessions/{sid}/close"))
        )
        t.start()
        t.join(timeout=5)
    r = result[0]
    assert r.status_code == 409 and r.json()["code"] == "gm_busy"
    _clean(r.json(), sid)
    assert p.repo.get_session(sid).status == "open" and _closed_lines(p, sid) == 0
    assert _act(client, sid).status_code == 202  # no close left holding turns out


# --- TP-V5-15 (part 1) ------------------------------------------------------- #
def test_tp_v5_15_a_gm_write_does_not_block_a_replace_and_its_session_closes() -> None:
    p, _client = _app()
    sid = _start(_client)
    client = world_client(play=p)
    raw = _file("w").model_dump(mode="json")
    with p.guard.hold(sid):  # a GM write waiting on its LLM
        r = client.post("/api/world/worlds/w/file?confirm=true", json=raw)
    assert r.status_code == 200, r.text
    assert r.json()["closed_session_ids"] == [sid]
    assert p.repo.get_session(sid).status == "closed" and _closed_lines(p, sid) == 1


def test_tp_v5_15_a_turn_blocks_a_replace_with_sessions_busy() -> None:
    p, _client = _app()
    sid = _start(_client)
    client = world_client(play=p)
    raw = _file("w").model_dump(mode="json")
    p.guard.acquire(sid, "run-1")
    try:
        r = client.post("/api/world/worlds/w/file?confirm=true", json=raw)
    finally:
        p.guard.release(sid)
    assert r.status_code == 409 and r.json()["code"] == "sessions_busy"
    assert p.repo.get_session(sid).status == "open"


def test_tp_v5_15_a_session_whose_close_times_out_is_reported_busy_not_mid_turn() -> None:
    """§ 1.1 R-05b: the replace has happened; the warning says why the session stays open."""
    p, _client = _app(tuning=PlayTuning(gm_write_wait_s=0.05))
    sid = _start(_client)
    client = world_client(play=p)
    raw = _file("w").model_dump(mode="json")
    result: list = []
    with p.guard.short_write(sid, timeout_s=1):  # a GM save section that will not end
        t = threading.Thread(
            target=lambda: result.append(
                client.post("/api/world/worlds/w/file?confirm=true", json=raw)
            )
        )
        t.start()
        t.join(timeout=5)
    r = result[0]
    assert r.status_code == 200 and r.json()["closed_session_ids"] == []
    messages = [w["message"] for w in r.json()["warnings"] if w["stage"] == "sessions"]
    assert messages == [f"session {sid} was busy and could not be closed"]
    assert p.repo.get_session(sid).status == "open"


# --- TP-V5-15 (part 2, Step 5.2) --------------------------------------------- #
def test_tp_v5_15_a_replace_during_a_gm_generate_closes_and_the_generate_gets_409() -> None:
    from locus.play import InMemoryPlayRepository
    from locus.play.rumor.generator import RumorGenerator
    from locus.play.turn.executor import SyncTurnExecutor
    from tests.api.play_fixtures import Loader
    from tests.play.concurrency import BlockingDrafts
    from tests.play.helpers import compose_play

    llm = BlockingDrafts()
    p = compose_play(
        InMemoryPlayRepository(), RumorGenerator(llm), Loader(), executor=SyncTurnExecutor()
    )
    gm_client = TestClient(create_app(play=p))
    sid = _start(gm_client)
    result: list = []
    t = threading.Thread(
        target=lambda: result.append(gm_client.post(f"/api/gm/sessions/{sid}/regions/r1/rumors"))
    )
    t.start()
    try:
        assert llm.wait_entered(1)  # the GM write holds its lease, drafting
        raw = _file("w").model_dump(mode="json")
        r = world_client(play=p).post("/api/world/worlds/w/file?confirm=true", json=raw)
    finally:
        llm.release()
        t.join(5)
    assert r.status_code == 200 and r.json()["closed_session_ids"] == [sid]
    generated = result[0]
    assert generated.status_code == 409 and generated.json()["code"] == "session_closed"
    assert p.repo.list_rumors(sid, include_pruned=True) == []


# --- rumor_inactive over HTTP (code review 01 #4) ---------------------------------- #
def test_a_support_change_on_a_switched_off_rumor_answers_409_rumor_inactive() -> None:
    p, client = _app()
    sid = _start(client)
    made = client.post(f"/api/gm/sessions/{sid}/regions/r1/rumors")
    assert made.status_code == 200, made.text
    rumor = p.repo.get_rumor(sid, made.json()[0]["id"])
    p.repo.upsert_rumor(rumor.model_copy(update={"active": False}))  # a void meanwhile
    r = client.put(f"/api/gm/sessions/{sid}/rumors/{rumor.id}/support", json={"support": 0.9})
    assert r.status_code == 409 and r.json() == {
        "detail": "the rumor is no longer active",
        "code": "rumor_inactive",
    }
    assert p.repo.get_rumor(sid, rumor.id).support == rumor.support
