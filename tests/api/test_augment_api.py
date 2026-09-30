"""augmentation-run endpoints on the world router (TestClient, mocked service)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from locus.world.augmentation.types import AugmentationQuestion, AugmentationRun, ChangeSet
from locus.world.wiring import WorldContainer


class _AugService:
    def start_run(self, world_id):
        return AugmentationRun(
            world_id=world_id,
            open_questions=[AugmentationQuestion(issue_id="i1", text="q?", options=["add"])],
        )

    def answer(self, run_id, answer):
        if run_id == "missing":
            raise LookupError("augmentation run not found: missing")
        return ChangeSet(description="applied")

    def revert(self, run_id, change_id):
        if run_id == "missing":
            raise LookupError("augmentation run not found")


def _client() -> TestClient:
    world = WorldContainer(
        builder=None,
        editor=None,
        augmentation=_AugService(),
        wiki_admin=None,
        cross_world=None,
        exporter=None,
        demo=None,
        cache=None,
        importer=None,
    )
    return TestClient(create_app(world=world))


def test_start_augmentation() -> None:
    r = _client().post("/api/world/worlds/w/augmentation/runs")
    assert r.status_code == 200
    assert len(r.json()["open_questions"]) == 1


def test_answer_ok() -> None:
    body = {"question_id": "q1", "action": "add", "statement": "lore"}
    r = _client().post("/api/world/augmentation/runs/s1/answer", json=body)
    assert r.status_code == 200
    assert r.json()["description"] == "applied"


def test_answer_missing_run_404() -> None:
    body = {"question_id": "q1", "action": "ignore"}
    r = _client().post("/api/world/augmentation/runs/missing/answer", json=body)
    assert r.status_code == 404


def test_revert_endpoint() -> None:
    r = _client().post("/api/world/augmentation/runs/s1/revert", params={"change_id": "c1"})
    assert r.status_code == 204
