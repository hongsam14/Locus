"""Play test fixtures (V5)."""

from __future__ import annotations

import pytest

from locus.play import InMemoryPlayRepository


@pytest.fixture(params=["memory", "sql"])
def threaded_repo(request, tmp_path):
    """A play repository two threads can share (V5 NFR § 2.1, NFR review R-02).

    ``sql`` is the SQLAlchemy adapter on a SQLite *file*: ``sqlite://`` would give each
    connection its own database, so two threads would never see the same rows. pysqlite
    takes no lock on a SELECT and locks on the first write, so reads inside a unit of
    work overlap too; ``FOR UPDATE`` is ignored there.
    """
    if request.param == "memory":
        yield InMemoryPlayRepository()
        return
    pytest.importorskip("sqlalchemy")
    from sqlalchemy import create_engine

    from locus.play.storage.postgres_repo import PostgresPlayRepository

    engine = create_engine(
        f"sqlite:///{tmp_path}/play.db",
        future=True,
        connect_args={"check_same_thread": False, "timeout": 5},
    )
    repo = PostgresPlayRepository(engine=engine)
    repo.ensure_schema()
    yield repo
    engine.dispose()
