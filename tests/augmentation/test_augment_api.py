"""U7 augmentation API tests — authoring augment endpoints (TestClient, mocked)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from locus.augmentation.types import AugmentationQuestion, AugmentationSession, ChangeSet


class _AugService:
    def start_session(self, world_id):
        return AugmentationSession(
            world_id=world_id,
            open_questions=[AugmentationQuestion(issue_id="i1", text="q?", options=["add"])],
        )

    def submit_answer(self, session_id, answer):
        if session_id == "missing":
            raise LookupError("session not found: missing")
        return ChangeSet(description="applied")

    def revert(self, session_id, change_id):
        if session_id == "missing":
            raise LookupError("session not found")


def _client() -> TestClient:
    return TestClient(create_app(augmentation_service=_AugService()))


def test_start_augmentation() -> None:
    r = _client().post("/api/authoring/worlds/w/augment/session")
    assert r.status_code == 200
    assert len(r.json()["open_questions"]) == 1


def test_submit_answer_ok() -> None:
    body = {"question_id": "q1", "action": "add", "statement": "lore"}
    r = _client().post("/api/authoring/augment/s1/answer", json=body)
    assert r.status_code == 200
    assert r.json()["description"] == "applied"


def test_submit_answer_missing_session_404() -> None:
    body = {"question_id": "q1", "action": "ignore"}
    r = _client().post("/api/authoring/augment/missing/answer", json=body)
    assert r.status_code == 404


def test_revert_endpoint() -> None:
    r = _client().post("/api/authoring/augment/s1/revert", params={"change_id": "c1"})
    assert r.status_code == 204
