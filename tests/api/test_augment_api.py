"""augmentation-run endpoints on the world router (TestClient, mocked service).

U3 intended change (C-3, 〔Step 1.3 정정〕 BLM §7): ``answer`` returns ``AnswerResult``,
``revert`` returns 200 with the run (was 204), refusals are 409, ``GET`` reads a kept
run and ``unignore`` asks an ignored issue again.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from locus.world.augmentation.types import (
    AnswerResult,
    AugmentationQuestion,
    AugmentationRun,
    ChangeSet,
    QuestionTarget,
    RevertOrderError,
    RunFinishedError,
)
from locus.world.wiring import WorldContainer


def _run(world_id: str = "w") -> AugmentationRun:
    return AugmentationRun(
        id="s1",
        world_id=world_id,
        open_questions=[
            AugmentationQuestion(
                issue_id="i1",
                issue_key="gap:region:r1::",
                text="q?",
                target=QuestionTarget(kind="region", id="r1", name="Riverton"),
                actions=["add", "ignore"],
            )
        ],
    )


class _AugService:
    def start_run(self, world_id):
        return _run(world_id)

    def get_run(self, run_id):
        return _run() if run_id == "s1" else None

    def answer(self, run_id, answer):
        if run_id == "missing":
            raise LookupError("augmentation run not found: missing")
        if run_id == "done":
            raise RunFinishedError("this run is finished; start a new one")
        if answer.action == "add" and not answer.statement:
            raise ValueError("an added fact needs a statement")
        return AnswerResult(change=ChangeSet(description="applied"), run=_run())

    def revert(self, run_id, change_id):
        if run_id == "missing":
            raise LookupError("augmentation run not found")
        if change_id == "old":
            raise RevertOrderError("revert the later changes first")
        return _run()

    def unignore(self, run_id, issue_key):
        if issue_key == "nope":
            raise LookupError("not an ignored issue")
        return _run()


def _client() -> TestClient:
    world = WorldContainer(
        builder=None,
        editors=None,
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
    (q,) = r.json()["open_questions"]
    assert q["target"]["name"] == "Riverton" and q["actions"] == ["add", "ignore"]
    assert "options" not in q


def test_answer_ok() -> None:
    body = {"question_id": "q1", "action": "add", "statement": "lore"}
    r = _client().post("/api/world/augmentation/runs/s1/answer", json=body)
    assert r.status_code == 200
    assert r.json()["change"]["description"] == "applied"
    assert r.json()["run"]["id"] == "s1"


def test_answer_missing_run_404() -> None:
    body = {"question_id": "q1", "action": "ignore"}
    r = _client().post("/api/world/augmentation/runs/missing/answer", json=body)
    assert r.status_code == 404


def test_answer_refusals_are_400_and_409() -> None:
    client = _client()
    bad = client.post(
        "/api/world/augmentation/runs/s1/answer", json={"question_id": "q1", "action": "add"}
    )
    assert bad.status_code == 400
    done = client.post(
        "/api/world/augmentation/runs/done/answer", json={"question_id": "q1", "action": "ignore"}
    )
    assert done.status_code == 409


def test_revert_endpoint() -> None:
    client = _client()
    r = client.post("/api/world/augmentation/runs/s1/revert", params={"change_id": "c1"})
    assert r.status_code == 200 and r.json()["id"] == "s1"
    old = client.post("/api/world/augmentation/runs/s1/revert", params={"change_id": "old"})
    assert old.status_code == 409


def test_get_run_and_unignore() -> None:
    client = _client()
    assert client.get("/api/world/augmentation/runs/s1").status_code == 200
    assert client.get("/api/world/augmentation/runs/gone").status_code == 404  # restart
    r = client.post("/api/world/augmentation/runs/s1/unignore", json={"issue_key": "k"})
    assert r.status_code == 200
    r = client.post("/api/world/augmentation/runs/s1/unignore", json={"issue_key": "nope"})
    assert r.status_code == 404
