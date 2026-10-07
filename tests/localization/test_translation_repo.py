"""``TranslationStore`` contract across both adapters (in-memory, PostgreSQL-on-SQLite)
+ the domain-model guarantee that display-only ``*_ko`` fields no longer exist on
play models (FR-A2: localization is applied by the API layer, never persisted)."""

from __future__ import annotations

import pytest

pytest.importorskip("sqlalchemy")

from pydantic import ValidationError  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

from locus.localization.models import Translation  # noqa: E402
from locus.localization.storage.memory_repo import InMemoryTranslationRepository  # noqa: E402
from locus.localization.storage.postgres_repo import PostgresTranslationRepository  # noqa: E402
from locus.play.models import SessionRumor  # noqa: E402
from locus.shared.models import Provenance, SourceKind  # noqa: E402


def _pg() -> PostgresTranslationRepository:
    r = PostgresTranslationRepository(engine=create_engine("sqlite://", future=True))
    r.ensure_schema()
    return r


@pytest.fixture(params=["memory", "postgres"])
def store(request):
    return InMemoryTranslationRepository() if request.param == "memory" else _pg()


def _t(sid="s", field="statement", text="번역", h="h1") -> Translation:
    return Translation(
        source_kind="rumor", source_id=sid, source_field=field, text=text, source_hash=h
    )


def _get(store, sid, field="statement", lang="ko"):
    return store.get_many([("rumor", sid, field)], lang).get((sid, field))


def test_upsert_get_roundtrip(store) -> None:
    store.upsert_many([_t()])
    got = _get(store, "s")
    assert got is not None and got.text == "번역" and got.source_hash == "h1"


def test_upsert_overwrites_same_key(store) -> None:
    store.upsert_many([_t(text="old", h="h1")])
    store.upsert_many([_t(text="new", h="h2")])
    got = _get(store, "s")
    assert got.text == "new" and got.source_hash == "h2"


def test_get_missing_returns_none(store) -> None:
    assert _get(store, "nope") is None


def test_upsert_many_batch(store) -> None:
    store.upsert_many([_t(sid="a", text="A"), _t(sid="b", text="B")])
    assert _get(store, "a").text == "A"
    assert _get(store, "b").text == "B"


def test_upsert_many_is_idempotent_on_conflict(store) -> None:
    # same key twice -> one row, last value wins (ON CONFLICT DO UPDATE, U1 5.4/7.2)
    store.upsert_many([_t(sid="a", text="A", h="h1")])
    store.upsert_many([_t(sid="a", text="A2", h="h2")])
    got = _get(store, "a")
    assert got.text == "A2" and got.source_hash == "h2"
    out = store.get_many([("rumor", "a", "statement")], "ko")
    assert len(out) == 1


def test_get_many(store) -> None:
    store.upsert_many([_t(sid="a", text="A"), _t(sid="b", text="B")])
    out = store.get_many(
        [("rumor", "a", "statement"), ("rumor", "b", "statement"), ("rumor", "c", "statement")],
        "ko",
    )
    assert out[("a", "statement")].text == "A"
    assert out[("b", "statement")].text == "B"
    assert ("c", "statement") not in out


def test_play_models_carry_no_display_fields() -> None:
    """Domain models are boundary-clean: ``statement_ko`` is not a SessionRumor field."""
    with pytest.raises(ValidationError):
        SessionRumor(
            session_id="s",
            region_id="r1",
            distorted_from_id="k1",
            statement="hello",
            statement_ko="안녕",  # display-only -> belongs to api.schemas.RumorOut
            provenance=Provenance(source=SourceKind.SIMULATION),
        )


def test_reupsert_keeps_primary_key(store) -> None:
    first = _t("a", text="hello")
    store.upsert_many([first])
    store.upsert_many([_t("a", text="hello again")])
    row = store.get_many([("rumor", "a", "statement")], "ko")[("a", "statement")]
    assert row.text == "hello again"
    assert row.id == first.id  # ON CONFLICT never rewrites the PK


def test_purge_world_except_keeps_the_ids_still_held(store) -> None:  # V3 code review 01 #1
    def row(id_: str, world: str | None) -> Translation:
        return Translation(
            source_kind="region",
            source_id=id_,
            source_field="name",
            text="t",
            source_hash="h",
            world_id=world,
        )

    store.upsert_many(
        [row("kept", "w"), row("gone", "w"), row("elsewhere", "other"), row("loose", None)]
    )
    assert store.purge_world_except("w", {"kept"}) == 1

    def held(id_: str) -> bool:
        return (id_, "name") in store.get_many([("region", id_, "name")], "ko")

    assert held("kept") and not held("gone") and held("elsewhere") and held("loose")
