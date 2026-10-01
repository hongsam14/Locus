"""U4 play API — session start (dual response), player screen, act/poll, guard 409s,
run ownership, log (Step 8.4; EX-7/8/13/15/16, FD R-09, NFR R-03/R-06)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from locus.play.turn.executor import SyncTurnExecutor
from tests.api.play_fixtures import play_container


def _app(executor=None):
    p = play_container(executor=executor or SyncTurnExecutor())
    return p, TestClient(create_app(play=p))


def _start(client: TestClient, name: str = "Ari", region: str = "r1") -> dict:
    r = client.post("/api/play/worlds/w/sessions", json={"name": name, "start_region_id": region})
    assert r.status_code == 201, r.text
    return r.json()


def test_r09_session_start_keeps_the_bodyless_contract_and_adds_the_player_form() -> None:
    _p, client = _app()
    gm = client.post("/api/play/worlds/w/sessions")  # no body: GM session, as before
    assert gm.status_code == 200 and gm.json()["status"] == "open" and "player" not in gm.json()
    out = _start(client)
    assert set(out) == {"session", "player"}
    assert out["player"]["name"] == "Ari" and out["player"]["region_id"] == "r1"
    assert out["session"]["turn"] == 0
    bad_region = client.post(
        "/api/play/worlds/w/sessions", json={"name": "Ari", "start_region_id": "nowhere"}
    )
    assert bad_region.status_code == 400
    assert (
        client.post(
            "/api/play/worlds/missing/sessions", json={"name": "A", "start_region_id": "r1"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/play/worlds/w/sessions", json={"name": "", "start_region_id": "r1"}
        ).status_code
        == 422
    )


def test_ex13_region_screen_and_player_routes() -> None:
    _p, client = _app()
    out = _start(client)
    sid = out["session"]["id"]
    assert client.get(f"/api/play/sessions/{sid}/player").json()["id"] == out["player"]["id"]
    r = client.get(f"/api/play/sessions/{sid}/region")
    assert r.status_code == 200, r.text
    view = r.json()
    assert view["region_name"] == "R1" and view["level_path"] == ["R1"] and view["level"] == "town"
    assert view["facts"] and view["facts"][0]["statement"] == "fact"
    assert view["facts"][0]["statement_ko"] is None  # translation key present, cache-only
    assert view["hearsay"] == [] and view["rumors"] == [] and view["moves"] == []
    assert view["turn_running"] is False and view["llm_available"] is True
    gm_sid = client.post("/api/play/worlds/w/sessions").json()["id"]
    assert client.get(f"/api/play/sessions/{gm_sid}/region").status_code == 400  # no player
    assert client.get(f"/api/play/sessions/{gm_sid}/player").status_code == 404
    assert client.get("/api/play/sessions/nope/region").status_code == 404


def test_ex7_act_answers_202_and_the_poll_reports_done() -> None:
    _p, client = _app()
    sid = _start(client)["session"]["id"]
    r = client.post(f"/api/play/sessions/{sid}/act", json={"type": "wait"})
    assert r.status_code == 202, r.text
    run = r.json()
    assert (
        run["status"] == "running" and run["cost_turns"] == 1 and run["action"] == {"type": "wait"}
    )
    polled = client.get(f"/api/play/sessions/{sid}/turn-runs/{run['id']}")
    assert polled.status_code == 200 and polled.json()["status"] == "done"
    result = polled.json()["result"]
    assert result["session"]["turn"] == 1 and result["player"]["turns_spent"] == 1
    assert result["llm_available"] is True and result["llm_calls"] == 0
    runs = client.get(f"/api/play/sessions/{sid}/turn-runs", params={"status": "done"}).json()
    assert [x["id"] for x in runs] == [run["id"]]
    assert (
        client.get(f"/api/play/sessions/{sid}/turn-runs", params={"status": "running"}).json() == []
    )
    log = client.get(f"/api/play/sessions/{sid}/log").json()
    # U7 intended change: BR-U7-12 — the player's log hides the turn machinery
    assert [e["kind"] for e in log] == ["session_started", "player_waited"]
    gm_timeline = client.get(f"/api/gm/sessions/{sid}/timeline").json()
    assert gm_timeline[-1]["kind"] == "advance_turn"  # the GM still sees every line
    assert client.get(f"/api/play/sessions/{sid}/region").json()["turn"] == 1


def test_act_rejections_400_422_409() -> None:
    _p, client = _app()
    sid = _start(client)["session"]["id"]
    assert (
        client.post(
            f"/api/play/sessions/{sid}/act", json={"type": "move", "to_region_id": "zzz"}
        ).status_code
        == 400
    )
    assert client.post(f"/api/play/sessions/{sid}/act", json={"type": "fly"}).status_code == 422
    assert (
        client.post(
            f"/api/play/sessions/{sid}/act", json={"type": "end_talk", "npc_id": "ghost"}
        ).status_code
        == 400
    )
    gm_sid = client.post("/api/play/worlds/w/sessions").json()["id"]
    assert (
        client.post(f"/api/play/sessions/{gm_sid}/act", json={"type": "wait"}).status_code == 400
    )  # no player
    assert client.post(f"/api/play/sessions/{sid}/close").status_code == 200
    assert (
        client.post(f"/api/play/sessions/{sid}/act", json={"type": "wait"}).status_code == 409
    )  # closed


def test_ex8_guard_makes_writes_409_while_a_run_is_in_progress() -> None:
    p, client = _app()
    sid = _start(client)["session"]["id"]
    p.guard.acquire(sid, "run-x")  # simulate a background run holding the session
    try:
        assert (
            client.post(f"/api/play/sessions/{sid}/act", json={"type": "wait"}).status_code == 409
        )
        assert client.post(f"/api/gm/sessions/{sid}/advance").status_code == 409
        assert (
            client.put(
                f"/api/gm/sessions/{sid}/regions/r1/distortion", json={"degree": 0.5}
            ).status_code
            == 409
        )
        assert client.post(f"/api/gm/sessions/{sid}/regions/r1/rumors").status_code == 409
        assert (
            client.post(
                f"/api/gm/sessions/{sid}/events",
                json={"region_id": "r1", "category": "war", "magnitude": 0.5},
            ).status_code
            == 409
        )
        assert client.post(f"/api/play/sessions/{sid}/close").status_code == 409
        view = client.get(f"/api/play/sessions/{sid}/region")  # reads are never blocked
        assert view.status_code == 200 and view.json()["turn_running"] is True
        assert client.get(f"/api/gm/sessions/{sid}/distortions").status_code == 200
        assert client.get(f"/api/gm/sessions/{sid}/timeline").status_code == 200
    finally:
        p.guard.release(sid)
    assert client.post(f"/api/gm/sessions/{sid}/advance").status_code == 200  # idle again


def test_r06_turn_run_lookup_is_session_scoped() -> None:
    _p, client = _app()
    a = _start(client)["session"]["id"]
    b = client.post("/api/play/worlds/w/sessions").json()["id"]
    run = client.post(f"/api/play/sessions/{a}/act", json={"type": "wait"}).json()
    assert client.get(f"/api/play/sessions/{b}/turn-runs/{run['id']}").status_code == 404
    assert client.get(f"/api/play/sessions/{a}/turn-runs/{run['id']}").status_code == 200
    assert client.get("/api/play/sessions/nope/turn-runs").status_code == 404


def test_nfr_r03_act_makes_no_llm_call_and_opens_one_unit_of_work_before_202() -> None:
    """Structural responsiveness gate: the request path (before the executor takes the
    run) opens exactly one unit of work and never touches the LLM."""

    class RecordingExecutor:
        def __init__(self) -> None:
            self.uow_at_submit = -1

        def submit(self, fn, *args):
            self.uow_at_submit = counter["uow"]
            fn(*args)

        def shutdown(self, timeout):  # pragma: no cover
            return None

    counter = {"uow": 0}
    executor = RecordingExecutor()
    p, client = _app(executor=executor)
    real_uow = p.repo.uow

    def counting_uow():
        counter["uow"] += 1
        return real_uow()

    p.repo.uow = counting_uow  # type: ignore[method-assign]
    sid = _start(client)["session"]["id"]  # 1 UoW (session start)
    counter["uow"] = 0
    calls = {"llm": 0}
    gen = p.rumors._gen  # type: ignore[union-attr]
    real_chain = gen.generate_chain

    def counting_chain(**kw):
        calls["llm"] += len(kw["degrees"])
        return real_chain(**kw)

    gen.generate_chain = counting_chain  # type: ignore[method-assign]
    r = client.post(f"/api/play/sessions/{sid}/act", json={"type": "wait"})
    assert r.status_code == 202
    assert executor.uow_at_submit == 1  # exactly one UoW before the run was handed over
    assert calls["llm"] == 0  # a wait without events drafts nothing


def test_gm_advance_response_is_still_a_turn_result() -> None:  # EX-18 / contract (2)
    _p, client = _app()
    sid = _start(client)["session"]["id"]
    r = client.post(f"/api/gm/sessions/{sid}/advance")
    assert r.status_code == 200
    body = r.json()
    assert body["turn"] == 1 and body["session_id"] == sid and "region_changes" in body
    assert body["llm_calls"] == 0 and body["rumors_capped_regions"] == []


def test_u4_2_a_shut_down_executor_answers_503_not_500() -> None:
    """Code review U4-2 #14: `submit` raised a bare RuntimeError that PLAY_ERRORS did
    not catch, so the request 500'd with the player already moved."""
    from locus.play.turn.executor import ThreadTurnExecutor

    executor = ThreadTurnExecutor(name="turn-503-test")
    p, client = _app(executor=executor)
    sid = _start(client)["session"]["id"]
    executor.shutdown(timeout=2)  # e.g. a graceful shutdown racing a request
    r = client.post(f"/api/play/sessions/{sid}/act", json={"type": "wait"})
    assert r.status_code == 503
    assert not p.guard.is_running(sid)  # and the guard was released
    assert client.get(f"/api/play/sessions/{sid}/turn-runs").json()[0]["status"] == "failed"


def test_u4_2_event_suggestion_is_guarded_like_every_other_gm_write() -> None:
    """Code review U4-2 #15: suggest was the only GM write route without the guard."""
    p, client = _app()
    sid = _start(client)["session"]["id"]
    p.guard.acquire(sid, "run-x")
    try:
        assert client.post(f"/api/gm/sessions/{sid}/events/suggest").status_code == 409
    finally:
        p.guard.release(sid)
