"""S1 SessionService tests — world validation + default-distortion seeding."""

from __future__ import annotations

import pytest

from locus.session import InMemorySessionRepository, SessionService, WorldNotFoundError
from locus.session.models import DEFAULT_DISTORTION_DEGREE, SessionStatus
from locus.storage.base import Node


class FakeGraph:
    """Minimal GraphRepository stub exposing find_nodes for regions."""

    def __init__(self, regions_by_world: dict[str, list[str]]) -> None:
        self._regions = regions_by_world

    def find_nodes(self, world_id: str, label: str, filters=None) -> list[Node]:
        if label != "Region":
            return []
        return [
            Node(id=rid, label="Region", world_id=world_id, properties={"id": rid})
            for rid in self._regions.get(world_id, [])
        ]


def _service(regions: dict[str, list[str]]) -> tuple[SessionService, InMemorySessionRepository]:
    repo = InMemorySessionRepository()
    return SessionService(repo, FakeGraph(regions)), repo


def test_start_session_seeds_default_distortion_for_all_regions() -> None:
    svc, repo = _service({"w": ["r1", "r2", "r3"]})
    session = svc.start_session("w")
    assert session.status == SessionStatus.OPEN.value and session.turn == 0
    distortions = {
        d.region_id: d.distortion_degree for d in repo.list_region_distortions(session.id)
    }
    assert distortions == {
        "r1": DEFAULT_DISTORTION_DEGREE,
        "r2": DEFAULT_DISTORTION_DEGREE,
        "r3": DEFAULT_DISTORTION_DEGREE,
    }


def test_start_session_rejects_unknown_world() -> None:
    svc, _ = _service({"w": ["r1"]})
    with pytest.raises(WorldNotFoundError):
        svc.start_session("nonexistent")


def test_lifecycle_and_history() -> None:
    svc, _ = _service({"w": ["r1"]})
    a = svc.start_session("w")
    b = svc.start_session("w")
    assert {s.id for s in svc.list_sessions("w")} == {a.id, b.id}
    closed = svc.close_session(a.id)
    assert closed.status == SessionStatus.CLOSED.value
    assert svc.get_session(a.id).status == SessionStatus.CLOSED.value


def test_get_and_timeline_missing_raise_lookup() -> None:
    svc, _ = _service({"w": ["r1"]})
    with pytest.raises(LookupError):
        svc.get_session("missing")
    with pytest.raises(LookupError):
        svc.get_timeline("missing")
    with pytest.raises(LookupError):
        svc.close_session("missing")


def test_timeline_empty_for_new_session() -> None:
    svc, _ = _service({"w": ["r1"]})
    s = svc.start_session("w")
    assert svc.get_timeline(s.id) == []
