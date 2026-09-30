"""play + gm router tests — FastAPI TestClient with an in-memory PlayContainer."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from tests.api.play_fixtures import play_container


def _client(*, with_suggester: bool = False) -> TestClient:
    return TestClient(create_app(play=play_container(with_suggester=with_suggester)))


def _new_session(client: TestClient) -> str:
    return client.post("/api/play/worlds/w/sessions").json()["id"]


# --- play: sessions ------------------------------------------------------------ #
def test_start_list_get_close_flow() -> None:
    client = _client()
    r = client.post("/api/play/worlds/w/sessions")
    assert r.status_code == 200
    session = r.json()
    assert session["status"] == "open" and session["turn"] == 0
    sid = session["id"]

    hist = client.get("/api/play/worlds/w/sessions")
    assert hist.status_code == 200 and len(hist.json()) == 1

    got = client.get(f"/api/play/sessions/{sid}")
    assert got.status_code == 200 and got.json()["id"] == sid

    closed = client.post(f"/api/play/sessions/{sid}/close")
    assert closed.status_code == 200 and closed.json()["status"] == "closed"

    timeline = client.get(f"/api/gm/sessions/{sid}/timeline")
    # U4 (BR-U4-5): closing writes one SESSION_CLOSED entry; GM start writes none (R-09)
    assert timeline.status_code == 200
    assert [e["kind"] for e in timeline.json()] == ["session_closed"]


def test_start_unknown_world_404() -> None:
    assert _client().post("/api/play/worlds/missing/sessions").status_code == 404


def test_get_missing_session_404() -> None:
    client = _client()
    assert client.get("/api/play/sessions/nope").status_code == 404
    assert client.post("/api/play/sessions/nope/close").status_code == 404
    assert client.get("/api/gm/sessions/nope/timeline").status_code == 404


# --- gm: rumors / distortion / turn ---------------------------------------------- #
def test_generate_support_advance_and_knowledge_flow() -> None:
    client = _client()
    sid = _new_session(client)

    gen = client.post(f"/api/gm/sessions/{sid}/regions/r1/rumors")
    assert gen.status_code == 200
    rumors = gen.json()
    assert len(rumors) == 3
    rid = rumors[0]["id"]
    assert rumors[0]["statement_ko"] is None  # DTO field, no localization wired

    sup = client.put(f"/api/gm/sessions/{sid}/rumors/{rid}/support", json={"support": 0.9})
    assert sup.status_code == 200 and sup.json()["support"] == 0.9

    turn = client.post(f"/api/gm/sessions/{sid}/advance")
    assert turn.status_code == 200
    body = turn.json()
    assert body["turn"] == 1 and rid in body["promoted_ids"]

    listed = client.get(f"/api/gm/sessions/{sid}/regions/r1/rumors")
    assert listed.status_code == 200 and len(listed.json()) == 3  # read-only list

    know = client.get(f"/api/play/sessions/{sid}/regions/r1/knowledge")
    assert know.status_code == 200
    assert rid in know.json()["unique_ids"]  # promoted rumor is direct-like
    promoted = next(it for it in know.json()["items"] if it["knowledge_id"] == rid)
    assert promoted["source"] == "rumor:promoted" and promoted["is_hearsay"] is False


def test_set_distortion_and_regen() -> None:
    client = _client()
    sid = _new_session(client)
    dist = client.put(f"/api/gm/sessions/{sid}/regions/r1/distortion", json={"degree": 0.8})
    assert dist.status_code == 200 and dist.json()["distortion_degree"] == 0.8
    regen = client.post(f"/api/gm/sessions/{sid}/regions/r1/rumors/regen")
    assert regen.status_code == 200


def test_validation_and_status_codes() -> None:
    client = _client()
    sid = _new_session(client)
    assert client.post("/api/gm/sessions/nope/regions/r1/rumors").status_code == 404
    assert client.get("/api/gm/sessions/nope/regions/r1/rumors").status_code == 404
    assert client.post("/api/gm/sessions/nope/advance").status_code == 404
    # closed session -> 409
    client.post(f"/api/play/sessions/{sid}/close")
    assert client.post(f"/api/gm/sessions/{sid}/regions/r1/rumors").status_code == 409
    assert client.post(f"/api/gm/sessions/{sid}/advance").status_code == 409


# --- gm: events ------------------------------------------------------------------ #
def test_event_create_list_resolve_flow() -> None:
    client = _client()
    sid = _new_session(client)

    created = client.post(
        f"/api/gm/sessions/{sid}/events",
        json={"region_id": "r1", "category": "war", "description": "siege", "magnitude": 0.7},
    )
    assert created.status_code == 200
    ev = created.json()
    assert ev["status"] == "active" and ev["lifecycle"] == "persistent" and ev["category"] == "war"
    eid = ev["id"]

    listed = client.get(f"/api/gm/sessions/{sid}/events")
    assert listed.status_code == 200 and len(listed.json()) == 1
    assert client.get(f"/api/gm/sessions/{sid}/events?status=active").json()[0]["id"] == eid

    resolved = client.post(f"/api/gm/sessions/{sid}/events/{eid}/resolve")
    assert resolved.status_code == 200 and resolved.json()["status"] == "resolved"
    assert client.get(f"/api/gm/sessions/{sid}/events?status=active").json() == []


def test_event_validation_and_status_codes() -> None:
    client = _client()
    sid = _new_session(client)
    bad = client.post(
        f"/api/gm/sessions/{sid}/events",
        json={"region_id": "ghost", "category": "war", "magnitude": 0.5},
    )
    assert bad.status_code == 404
    clamped = client.post(
        f"/api/gm/sessions/{sid}/events",
        json={"region_id": "r1", "category": "war", "magnitude": 9.0},
    )
    assert clamped.status_code == 200 and clamped.json()["magnitude"] == 1.0
    assert (
        client.post(
            f"/api/gm/sessions/{sid}/events",
            json={"region_id": "r1", "category": "nonsense", "magnitude": 0.5},
        ).status_code
        == 422
    )
    ev = client.post(
        f"/api/gm/sessions/{sid}/events",
        json={"region_id": "r1", "category": "war", "magnitude": 0.5},
    ).json()
    assert client.delete(f"/api/gm/sessions/{sid}/events/{ev['id']}").status_code == 400
    assert client.get("/api/gm/sessions/nope/events").status_code == 404
    client.post(f"/api/play/sessions/{sid}/close")
    assert (
        client.post(
            f"/api/gm/sessions/{sid}/events",
            json={"region_id": "r1", "category": "war", "magnitude": 0.5},
        ).status_code
        == 409
    )


def test_suggest_approve_advance_flow() -> None:
    client = _client(with_suggester=True)
    sid = _new_session(client)
    sug = client.post(f"/api/gm/sessions/{sid}/events/suggest?n=1")
    assert sug.status_code == 200 and len(sug.json()) == 1
    ev = sug.json()[0]
    assert ev["status"] == "suggested"

    ap = client.post(f"/api/gm/sessions/{sid}/events/{ev['id']}/approve")
    assert ap.status_code == 200 and ap.json()["status"] == "active"

    turn = client.post(f"/api/gm/sessions/{sid}/advance")
    assert turn.status_code == 200
    body = turn.json()
    assert body["turn"] == 1 and ev["id"] in body["applied_event_ids"]


def test_suggest_without_suggester_empty() -> None:
    client = _client()
    sid = _new_session(client)
    r = client.post(f"/api/gm/sessions/{sid}/events/suggest")
    assert r.status_code == 200 and r.json() == []


def test_approve_missing_event_404() -> None:
    client = _client()
    sid = _new_session(client)
    assert client.post(f"/api/gm/sessions/{sid}/events/nope/approve").status_code == 404


def test_list_distortions() -> None:
    client = _client()
    sid = _new_session(client)
    seeded = client.get(f"/api/gm/sessions/{sid}/distortions").json()
    assert {r["region_id"] for r in seeded} == {"r1"}
    client.put(f"/api/gm/sessions/{sid}/regions/r1/distortion", json={"degree": 0.7})
    rows = client.get(f"/api/gm/sessions/{sid}/distortions").json()
    r1 = next(r for r in rows if r["region_id"] == "r1")
    assert r1["distortion_degree"] == 0.7
    assert client.get("/api/gm/sessions/nope/distortions").status_code == 404
