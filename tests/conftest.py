"""Repo-wide pytest configuration: hypothesis profile (PBT-08, NFR R-04).

``print_blob=True`` prints a ``@reproduce_failure`` blob for every failing
example; ``deadline=None`` keeps slow CI machines from flaking property tests.
Re-run one seed with ``pytest --hypothesis-seed=<n>``.
"""

from __future__ import annotations

import os
import weakref
from collections.abc import Iterator

import pytest
from hypothesis import settings

settings.register_profile("locus", print_blob=True, deadline=None)
settings.load_profile("locus")


@pytest.fixture(autouse=True, scope="session")
def _data_dir_outside_the_repo(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """World File backups go to a temporary folder, not ``./data`` (V9 code review 01 #7).

    ``Settings()`` defaults ``LOCUS_DATA_DIR`` to ``data``: a test that replaced a world
    through the API wrote its backup into the repo's ``data/backups`` on every run. A test
    that wants its own folder still passes ``data_dir`` (or sets the variable) itself.
    """
    old = os.environ.get("LOCUS_DATA_DIR")
    os.environ["LOCUS_DATA_DIR"] = str(tmp_path_factory.mktemp("locus-data"))
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("LOCUS_DATA_DIR", None)
        else:
            os.environ["LOCUS_DATA_DIR"] = old


# Engines seen connecting so far, and those first seen in the running test (V9, FR-T6).
_seen_engines: weakref.WeakSet = weakref.WeakSet()
_engines_of_this_test: list | None = None


def _track_engine(conn) -> None:  # an Engine "engine_connect" listener
    engine = conn.engine
    if engine in _seen_engines:
        return
    _seen_engines.add(engine)
    if _engines_of_this_test is not None:
        _engines_of_this_test.append(engine)


try:  # the play extras are optional
    from sqlalchemy import event as _sa_event
    from sqlalchemy.engine import Engine as _Engine
except ImportError:  # pragma: no cover - sqlalchemy is a dev dependency
    _Engine = None
else:
    _sa_event.listen(_Engine, "engine_connect", _track_engine)


@pytest.fixture(autouse=True)
def _dispose_sql_engines() -> Iterator[None]:
    """Close the SQLAlchemy engines a test first connected, when the test ends (V9, FR-T6).

    Tests open SQLite engines (in memory, or through an adapter built from a URL) and used
    to leave their connections to the garbage collector, which then printed ~50
    ``ResourceWarning: unclosed database`` lines under whatever test happened to be running.
    Only an engine whose first connection falls inside the test is disposed: an engine a
    wider fixture set up and connected before the test is that fixture's to close (code
    review 01 #21). A wider fixture's engine must therefore connect when it is set up.
    """
    global _engines_of_this_test
    _engines_of_this_test = mine = []
    try:
        yield
    finally:
        _engines_of_this_test = None
        for engine in mine:
            engine.dispose()
