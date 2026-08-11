"""Translation cache CRUD across both SessionRepository adapters (X1 / BR-X1-5..9)
plus verification that the response-only ``statement_ko`` is not persisted (P-F5)."""

from __future__ import annotations

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy import create_engine  # noqa: E402

from locus.models import Provenance, SourceKind  # noqa: E402
from locus.session.memory_repo import InMemorySessionRepository  # noqa: E402
from locus.session.models import SessionRumor, Translation  # noqa: E402
from locus.storage.postgres_session_repo import PostgresSessionRepository  # noqa: E402


def _pg() -> PostgresSessionRepository:
    r = PostgresSessionRepository(engine=create_engine("sqlite://", future=True))
    r.ensure_schema()
    return r


@pytest.fixture(params=["memory", "postgres"])
def repo(request):
    return InMemorySessionRepository() if request.param == "memory" else _pg()


def _t(sid="s", field="statement", text="번역", h="h1") -> Translation:
    return Translation(
        source_kind="rumor", source_id=sid, source_field=field, text=text, source_hash=h
    )


def test_upsert_get_roundtrip(repo) -> None:
    repo.upsert_translation(_t())
    got = repo.get_translation("rumor", "s", "statement", "ko")
    assert got is not None and got.text == "번역" and got.source_hash == "h1"


def test_upsert_overwrites_same_key(repo) -> None:
    repo.upsert_translation(_t(text="old", h="h1"))
    repo.upsert_translation(_t(text="new", h="h2"))
    got = repo.get_translation("rumor", "s", "statement", "ko")
    assert got.text == "new" and got.source_hash == "h2"


def test_get_missing_returns_none(repo) -> None:
    assert repo.get_translation("rumor", "nope", "statement", "ko") is None


def test_upsert_translations_batch(repo) -> None:
    repo.upsert_translations([_t(sid="a", text="A"), _t(sid="b", text="B")])
    assert repo.get_translation("rumor", "a", "statement", "ko").text == "A"
    assert repo.get_translation("rumor", "b", "statement", "ko").text == "B"


def test_upsert_translations_is_idempotent_on_conflict(repo) -> None:
    # re-upserting the same key (review #6 path) updates rather than raising
    repo.upsert_translations([_t(sid="a", text="A", h="h1")])
    repo.upsert_translations([_t(sid="a", text="A2", h="h2")])
    got = repo.get_translation("rumor", "a", "statement", "ko")
    assert got.text == "A2" and got.source_hash == "h2"


def test_get_translations_many(repo) -> None:
    repo.upsert_translation(_t(sid="a", text="A"))
    repo.upsert_translation(_t(sid="b", text="B"))
    out = repo.get_translations_many(
        [("rumor", "a", "statement"), ("rumor", "b", "statement"), ("rumor", "c", "statement")],
        "ko",
    )
    assert out[("a", "statement")].text == "A"
    assert out[("b", "statement")].text == "B"
    assert ("c", "statement") not in out


def test_statement_ko_not_persisted_in_postgres() -> None:
    repo = _pg()
    session = repo.create_session("w")
    rumor = SessionRumor(
        session_id=session.id,
        region_id="r1",
        distorted_from_id="k1",
        statement="hello",
        statement_ko="안녕",  # response-only; must not round-trip through the DB
        provenance=Provenance(source=SourceKind.SESSION_RUMOR),
    )
    repo.upsert_rumor(rumor)
    reloaded = repo.get_rumor(session.id, rumor.id)
    assert reloaded is not None
    assert reloaded.statement == "hello"
    assert reloaded.statement_ko is None  # P-F5: not persisted (explicit-column mapping)
