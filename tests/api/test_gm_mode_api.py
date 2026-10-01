"""U7 GM mode & hardening — the HTTP contract (Step 7.4; business-logic-model §9)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from locus.shared.models import Region, RegionLevel, RegionTopology
from tests.api.play_fixtures import Loader, _prov, play_container


def _app(**kw):
    p = play_container(**kw)
    return p, TestClient(create_app(play=p))


def _start(client: TestClient) -> str:
    out = client.post(
        "/api/play/worlds/w/sessions", json={"name": "Ari", "start_region_id": "r1"}
    ).json()
    return out["session"]["id"]


def _count(p, names):
    calls = dict.fromkeys(names, 0)
    for name in names:
        real = getattr(p.repo, name)

        def counted(*a, _real=real, _name=name, **kw):
            calls[_name] += 1
            return _real(*a, **kw)

        setattr(p.repo, name, counted)
    return calls


def test_contract_1_state_gives_one_row_per_region_with_counts() -> None:
    p, client = _app()
    sid = _start(client)
    client.post(
        f"/api/gm/sessions/{sid}/events",
        json={"region_id": "r1", "category": "war", "magnitude": 0.5},
    )
    state = client.get(f"/api/gm/sessions/{sid}/state")
    assert state.status_code == 200
    body = state.json()
    assert body["session_id"] == sid and body["player_region_id"] == "r1"
    (row,) = body["regions"]
    assert (row["region_id"], row["region_name"], row["active_events"]) == ("r1", "R1", 1)
    assert client.get("/api/gm/sessions/nope/state").status_code == 404


def test_contract_2_distortions_list_every_world_region_with_its_share() -> None:
    p, client = _app()
    sid = _start(client)
    loader: Loader = p.distortions._snapshots  # type: ignore[attr-defined]
    late = Region(world_id="w", name="Late", level=RegionLevel.TOWN, provenance=_prov())
    loader._topo = RegionTopology(world_id="w", regions=[loader.region, late])
    rows = client.get(f"/api/gm/sessions/{sid}/distortions").json()
    assert [(r["region_id"], r["feedback_share"]) for r in rows] == [("r1", 0.0), (late.id, 0.0)]


def test_contract_3_setting_a_missing_region_is_404_and_a_set_returns_the_row() -> None:
    _p, client = _app()
    sid = _start(client)
    missing = client.put(f"/api/gm/sessions/{sid}/regions/nowhere/distortion", json={"degree": 0.5})
    assert missing.status_code == 404
    ok = client.put(f"/api/gm/sessions/{sid}/regions/r1/distortion", json={"degree": 0.7})
    assert ok.status_code == 200
    assert ok.json() == {
        "session_id": sid,
        "region_id": "r1",
        "distortion_degree": 0.7,
        "feedback_share": 0.0,
    }


def test_contract_4_and_5_suggest_bounds_and_resolving_a_suggestion() -> None:
    _p, client = _app(with_suggester=True)
    sid = _start(client)
    for n in (0, 6):
        assert (
            client.post(f"/api/gm/sessions/{sid}/events/suggest", params={"n": n}).status_code
            == 400
        )
    (ev,) = client.post(f"/api/gm/sessions/{sid}/events/suggest", params={"n": 1}).json()
    assert client.post(f"/api/gm/sessions/{sid}/events/{ev['id']}/resolve").status_code == 400
    assert client.delete(f"/api/gm/sessions/{sid}/events/{ev['id']}").status_code == 204
    kinds = [e["kind"] for e in client.get(f"/api/gm/sessions/{sid}/timeline").json()]
    assert kinds[-2:] == ["event_suggested", "event_discarded"]


def test_contract_6_the_player_log_hides_the_gms_hand() -> None:
    _p, client = _app()
    sid = _start(client)
    client.put(f"/api/gm/sessions/{sid}/regions/r1/distortion", json={"degree": 0.9})
    client.post(f"/api/play/sessions/{sid}/act", json={"type": "wait"})
    log = [e["kind"] for e in client.get(f"/api/play/sessions/{sid}/log").json()]
    assert log == ["session_started", "player_waited"]
    gm = [e["kind"] for e in client.get(f"/api/gm/sessions/{sid}/timeline").json()]
    assert "set_distortion" in gm and "advance_turn" in gm


def test_contract_7_a_failed_npc_line_is_503_with_a_fixed_message() -> None:
    from locus.play import InMemoryPlayRepository
    from locus.play.rumor.generator import RumorGenerator
    from locus.play.turn.executor import SyncTurnExecutor
    from tests.api.play_fixtures import RumorLLM
    from tests.play.helpers import compose_play
    from tests.play.strategies import build_snapshot, npc
    from tests.shared.snapshots import StaticSnapshots

    class Down:
        def structured(self, prompt, schema, *, system=None):  # pragma: no cover
            raise AssertionError("no structured call here")

        def complete(self, prompt, *, system=None):
            raise RuntimeError("upstream 500: key sk-secret rejected")

    world = build_snapshot(["r1"], [], npcs=[npc("n1", "r1", name="Mara")])
    p = compose_play(
        InMemoryPlayRepository(),
        RumorGenerator(RumorLLM()),
        StaticSnapshots(world),
        executor=SyncTurnExecutor(),
        dialogue_llm=Down(),
    )
    client = TestClient(create_app(play=p))
    sid = _start(client)
    resp = client.post(f"/api/play/sessions/{sid}/npcs/n1/say", json={"text": "hello"})
    assert resp.status_code == 503
    assert resp.json()["detail"] == "the NPC could not answer right now; try again"
    assert "sk-secret" not in resp.text
    assert client.get(f"/api/play/sessions/{sid}/npcs").json()[0]["message_count"] == 0


def test_nfr_r05_log_and_distortions_read_the_store_twice() -> None:
    p, client = _app()
    sid = _start(client)
    calls = _count(p, ["get_session", "list_timeline", "list_region_distortions"])
    client.get(f"/api/play/sessions/{sid}/log")
    assert (calls["get_session"], calls["list_timeline"]) == (1, 1)
    calls.update(dict.fromkeys(calls, 0))
    client.get(f"/api/gm/sessions/{sid}/distortions")
    assert (calls["get_session"], calls["list_region_distortions"]) == (1, 1)
