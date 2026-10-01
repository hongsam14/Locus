"""U8 event seeds in a session (BLM §3, BR-U8-15..18, TP-U8-5, EX-4)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from locus.play import InMemoryPlayRepository
from locus.play.rumor.generator import RumorGenerator
from locus.play.turn.executor import SyncTurnExecutor
from locus.shared.models import EventSeed, Provenance, SourceKind, WorldSnapshot
from tests.api.play_fixtures import Loader, RumorLLM
from tests.play.helpers import compose_play


class _SeedLoader(Loader):
    def __init__(self) -> None:
        super().__init__()
        self.seeds = [
            EventSeed(
                id="seed-blight",
                world_id="w",
                region_id="r1",
                title="Blight in the fields",
                description="Grey spots spread through the fields.",
                category="plague",
                magnitude=0.5,
                provenance=Provenance(source=SourceKind.INPUT, generated_by="demo-author"),
            )
        ]

    def get(self, world_id) -> WorldSnapshot:
        snap = super().get(world_id)
        return WorldSnapshot(
            world_id=snap.world_id, kg=snap.kg, topo=snap.topo, event_seeds=self.seeds
        )


class _CountingLLM(RumorLLM):
    def __init__(self) -> None:
        self.calls = 0

    def structured(self, *a, **k):  # pragma: no cover - a seed never calls it
        self.calls += 1
        return super().structured(*a, **k)


def _client():
    llm = _CountingLLM()
    play = compose_play(
        InMemoryPlayRepository(), RumorGenerator(llm), _SeedLoader(), executor=SyncTurnExecutor()
    )
    client = TestClient(create_app(play=play))
    sid = client.post("/api/play/worlds/w/sessions").json()["id"]
    return client, play, sid, llm


def test_ex4_start_a_seed_then_409_then_resolve_and_start_again() -> None:
    """EX-4 / TP-U8-5: the seed becomes an ACTIVE plague event in its region, with its
    title on the timeline; a second start is 409 and leaves one ACTIVE event; after the
    event is resolved the seed starts again. No LLM call."""
    client, play, sid, llm = _client()
    seeds = client.get(f"/api/gm/sessions/{sid}/seeds").json()
    assert [(s["seed"]["id"], s["region_name"], s["running_event_id"]) for s in seeds] == [
        ("seed-blight", "R1", None)
    ]

    r = client.post(f"/api/gm/sessions/{sid}/seeds/seed-blight/start")
    assert r.status_code == 201
    event = r.json()
    assert (event["region_id"], event["category"], event["magnitude"]) == ("r1", "plague", 0.5)
    assert event["status"] == "active" and event["lifecycle"] == "persistent"
    line = [t for t in play.repo.list_timeline(sid) if t.kind == "event_created"][-1]
    assert line.payload["seed_title"] == "Blight in the fields"
    assert line.payload["seed_id"] == "seed-blight"
    running = client.get(f"/api/gm/sessions/{sid}/seeds").json()[0]["running_event_id"]
    assert running == event["id"]

    again = client.post(f"/api/gm/sessions/{sid}/seeds/seed-blight/start")
    assert again.status_code == 409 and "already running" in again.json()["detail"]
    active = play.repo.list_events(sid, "active")
    assert len(active) == 1

    assert client.post(f"/api/gm/sessions/{sid}/events/{event['id']}/resolve").status_code == 200
    assert client.get(f"/api/gm/sessions/{sid}/seeds").json()[0]["running_event_id"] is None
    assert client.post(f"/api/gm/sessions/{sid}/seeds/seed-blight/start").status_code == 201
    assert llm.calls == 0


def test_a_seed_start_is_refused_when_closed_busy_or_unknown() -> None:
    client, play, sid, _llm = _client()
    assert client.post(f"/api/gm/sessions/{sid}/seeds/nope/start").status_code == 404
    play.guard.acquire(sid, "run-1")
    try:
        busy = client.post(f"/api/gm/sessions/{sid}/seeds/seed-blight/start")
    finally:
        play.guard.release(sid)
    assert busy.status_code == 409 and "turn in progress" in busy.json()["detail"]
    play.repo.close_session(sid)
    closed = client.post(f"/api/gm/sessions/{sid}/seeds/seed-blight/start")
    assert closed.status_code == 409 and "closed" in closed.json()["detail"]
    assert client.get(f"/api/gm/sessions/{sid}/seeds").status_code == 200  # reads stay open
    assert client.get("/api/gm/sessions/nope/seeds").status_code == 404
