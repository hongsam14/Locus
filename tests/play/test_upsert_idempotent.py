"""U1 5.4 — ``INSERT ... ON CONFLICT`` upserts are idempotent on both play adapters:
the same key written twice leaves one row holding the last value."""

from __future__ import annotations

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy import create_engine  # noqa: E402

from locus.play.models import SessionRumor  # noqa: E402
from locus.play.storage.memory_repo import InMemoryPlayRepository  # noqa: E402
from locus.play.storage.postgres_repo import PostgresPlayRepository  # noqa: E402
from locus.shared.models import Provenance, SourceKind  # noqa: E402


def _pg() -> PostgresPlayRepository:
    r = PostgresPlayRepository(engine=create_engine("sqlite://", future=True))
    r.ensure_schema()
    return r


@pytest.fixture(params=["memory", "postgres"])
def repo(request):
    return InMemoryPlayRepository() if request.param == "memory" else _pg()


def _rumor(session_id: str, **kw) -> SessionRumor:
    base = {
        "session_id": session_id,
        "region_id": "r1",
        "distorted_from_id": "k1",
        "statement": "v1",
        "support": 0.2,
        "provenance": Provenance(source=SourceKind.SIMULATION),
    }
    base.update(kw)
    return SessionRumor(**base)


def test_rumor_upsert_twice_keeps_one_row_with_last_value(repo) -> None:
    session = repo.create_session("w")
    r = _rumor(session.id)
    repo.upsert_rumor(r)
    repo.upsert_rumor(r.model_copy(update={"statement": "v2", "support": 0.9}))
    rows = repo.list_rumors(session.id, "r1")
    assert len(rows) == 1
    assert rows[0].statement == "v2" and rows[0].support == 0.9


def test_rumor_batch_upsert_is_idempotent(repo) -> None:
    session = repo.create_session("w")
    r = _rumor(session.id)
    repo.upsert_rumors([r, r.model_copy(update={"statement": "v2"})])
    repo.upsert_rumors([r.model_copy(update={"statement": "v3"})])
    rows = repo.list_rumors(session.id, "r1")
    assert [x.statement for x in rows] == ["v3"]


def test_distortion_set_twice_keeps_one_row_with_last_value(repo) -> None:
    session = repo.create_session("w")
    repo.set_region_distortion(session.id, "r1", 0.3)
    repo.set_region_distortion(session.id, "r1", 0.8)
    rows = repo.list_region_distortions(session.id)
    assert len(rows) == 1 and rows[0].distortion_degree == 0.8
    assert repo.get_region_distortion(session.id, "r1") == 0.8
