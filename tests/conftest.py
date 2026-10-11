"""Repo-wide pytest configuration: hypothesis profile (PBT-08, NFR R-04).

``print_blob=True`` prints a ``@reproduce_failure`` blob for every failing
example; ``deadline=None`` keeps slow CI machines from flaking property tests.
Re-run one seed with ``pytest --hypothesis-seed=<n>``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from hypothesis import settings

settings.register_profile("locus", print_blob=True, deadline=None)
settings.load_profile("locus")


@pytest.fixture(autouse=True)
def _dispose_sql_engines() -> Iterator[None]:
    """Close every SQLAlchemy engine a test connected, when the test ends (V9, FR-T6).

    Tests open SQLite engines (in memory, or through an adapter built from a URL) and used
    to leave their connections to the garbage collector, which then printed ~50
    ``ResourceWarning: unclosed database`` lines under whatever test happened to be running.
    No engine is shared between tests (every fixture is function-scoped), so disposing at
    the end of each test is safe.
    """
    try:
        from sqlalchemy import event
        from sqlalchemy.engine import Connection, Engine
    except ImportError:  # the play extras are optional
        yield
        return
    engines: list[Engine] = []

    def track(conn: Connection) -> None:
        if conn.engine not in engines:
            engines.append(conn.engine)

    event.listen(Engine, "engine_connect", track)
    try:
        yield
    finally:
        event.remove(Engine, "engine_connect", track)
        for engine in engines:
            engine.dispose()
