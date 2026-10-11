"""The repo-wide test fixtures (V9 FR-T6, code review 01 #7, #21)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from locus.shared.config import Settings

_kept: dict = {}


@pytest.fixture(scope="module")
def module_engine():
    """An in-memory engine shared by two tests: it connects while it is set up."""
    engine = create_engine("sqlite://", future=True)
    with engine.begin() as conn:
        conn.execute(text("create table t (x int)"))
        conn.execute(text("insert into t values (1)"))
    yield engine
    engine.dispose()


def test_a_wider_fixtures_engine_lives_through_the_first_test(module_engine) -> None:
    with module_engine.connect() as conn:
        assert conn.execute(text("select count(*) from t")).scalar() == 1


def test_a_wider_fixtures_engine_lives_through_the_second_test(module_engine) -> None:
    # disposing it after the first test would have dropped the in-memory table (#21)
    with module_engine.connect() as conn:
        assert conn.execute(text("select count(*) from t")).scalar() == 1


def test_an_engine_a_test_opens_is_kept_for_the_next_check() -> None:
    engine = create_engine("sqlite://", future=True)
    with engine.connect() as conn:
        conn.execute(text("select 1"))
    _kept.update(engine=engine, pool=engine.pool)


def test_and_is_disposed_when_that_test_ended() -> None:
    assert _kept["engine"].pool is not _kept["pool"]  # dispose() swaps in a fresh pool


def test_backups_go_to_a_temporary_folder_not_the_repo() -> None:
    data = Settings().data_dir
    assert Path(os.environ["LOCUS_DATA_DIR"]) == data
    assert Path.cwd() not in data.resolve().parents and data.resolve() != Path("data").resolve()
