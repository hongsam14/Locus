"""U3's carry of U7 review items at the API (plan Step 7.6): NaN values and the 409
texts the web's ``conflictKind`` reads."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from tests.api.play_fixtures import play_container


def _client():
    play = play_container()
    return TestClient(create_app(play=play)), play


def _session(client: TestClient) -> str:
    return client.post("/api/play/worlds/w/sessions").json()["id"]


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "-Infinity", '"nan"', '"inf"'])
def test_gm_values_refuse_nan_and_infinity(raw: str) -> None:
    """U7 review §3: clamp01(NaN) is 1.0, so a NaN degree or support used to save 1.0."""
    client, _play = _client()
    sid = _session(client)
    head = {"content-type": "application/json"}
    r = client.put(
        f"/api/gm/sessions/{sid}/regions/r1/distortion",
        content=f'{{"degree": {raw}}}',
        headers=head,
    )
    assert r.status_code == 422
    r = client.post(
        f"/api/gm/sessions/{sid}/events",
        headers=head,
        content=f'{{"region_id": "r1", "category": "war", "magnitude": {raw}}}',
    )
    assert r.status_code == 422
    rumor = client.post(f"/api/gm/sessions/{sid}/regions/r1/rumors").json()[0]
    r = client.put(
        f"/api/gm/sessions/{sid}/rumors/{rumor['id']}/support",
        content=f'{{"support": {raw}}}',
        headers=head,
    )
    assert r.status_code == 422


def test_409_bodies_say_closed_or_busy() -> None:
    """#12: the web tells a closed session from a running turn by these words."""
    client, play = _client()
    sid = _session(client)
    play.guard.acquire(sid, "run-1")
    try:
        busy = client.put(f"/api/gm/sessions/{sid}/regions/r1/distortion", json={"degree": 0.4})
    finally:
        play.guard.release(sid)
    assert busy.status_code == 409 and "turn in progress" in busy.json()["detail"]
    play.repo.close_session(sid)
    closed = client.put(f"/api/gm/sessions/{sid}/regions/r1/distortion", json={"degree": 0.4})
    assert closed.status_code == 409 and "session is closed" in closed.json()["detail"]
