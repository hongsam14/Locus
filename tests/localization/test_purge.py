"""U5 translation purge (Step 5.4; FR-G4, BR-U5-19/22/33, TP-U5-6).

Both adapters (in-memory, PostgreSQL-on-SQLite) share the contract; the service also
forgets matching in-flight keys; and the API helper never asks for an en→en warm.
"""

from __future__ import annotations

import pytest

pytest.importorskip("sqlalchemy")

from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

from locus.localization import TranslationService  # noqa: E402
from locus.localization.models import Translation  # noqa: E402
from locus.localization.storage.memory_repo import InMemoryTranslationRepository  # noqa: E402
from locus.localization.storage.postgres_repo import PostgresTranslationRepository  # noqa: E402
from locus.localization.translator import Translator  # noqa: E402


def _pg() -> PostgresTranslationRepository:
    r = PostgresTranslationRepository(engine=create_engine("sqlite://", future=True))
    r.ensure_schema()
    return r


@pytest.fixture(params=["memory", "postgres"])
def store(request):
    return InMemoryTranslationRepository() if request.param == "memory" else _pg()


def _t(kind: str, sid: str, *, world=None, session=None, lang="ko") -> Translation:
    return Translation(
        source_kind=kind,
        source_id=sid,
        source_field="statement",
        target_lang=lang,
        text=f"{kind}:{sid}",
        source_hash="h",
        world_id=world,
        session_id=session,
    )


def _left(store) -> set[tuple[str, str]]:
    keys = [
        (k, s, "statement") for k in ("rumor", "knowledge", "event") for s in ("a", "b", "c", "d")
    ]
    return {(t.source_kind, t.source_id) for t in _all(store, keys)}


def _all(store, keys):
    out = []
    for kind, sid, field in keys:
        got = store.get_many([(kind, sid, field)], "ko")
        out += list(got.values())
    return out


def _seed(store) -> None:
    store.upsert_many(
        [
            _t("rumor", "a", session="s1"),
            _t("rumor", "b", session="s1"),
            _t("rumor", "c", session="s2"),
            _t("knowledge", "a", world="w1"),
            _t("knowledge", "d", world="w2"),
            _t("event", "b", session="s1"),
        ]
    )


def test_tp_u5_6_purge_by_kind_and_ids(store) -> None:
    _seed(store)
    assert store.purge(kind="rumor", ids=["a", "b"]) == 2
    assert _left(store) == {("rumor", "c"), ("knowledge", "a"), ("knowledge", "d"), ("event", "b")}


def test_tp_u5_6_purge_by_world_leaves_other_worlds(store) -> None:
    _seed(store)
    assert store.purge(kind="knowledge", world_id="w1") == 1
    assert ("knowledge", "d") in _left(store) and ("knowledge", "a") not in _left(store)


def test_tp_u5_6_purge_by_session(store) -> None:
    _seed(store)
    assert store.purge(session_id="s1") == 3  # rumors a, b and event b
    assert _left(store) == {("rumor", "c"), ("knowledge", "a"), ("knowledge", "d")}


def test_tp_u5_6_no_filter_refuses_and_deletes_nothing(store) -> None:
    _seed(store)
    with pytest.raises(ValueError, match="at least one filter"):
        store.purge()
    assert len(_left(store)) == 6
    assert store.purge(ids=[]) == 0  # an empty id list matches nothing, never "everything"
    assert len(_left(store)) == 6


def test_the_sql_purge_chunks_large_id_lists() -> None:
    pg = _pg()
    pg.upsert_many([_t("rumor", f"r{i}") for i in range(1200)])
    assert pg.purge(kind="rumor", ids=[f"r{i}" for i in range(1200)]) == 1200


@settings(max_examples=40)
@given(
    rows=st.lists(
        st.tuples(st.sampled_from(["rumor", "knowledge"]), st.sampled_from(list("abcdef"))),
        unique=True,
        max_size=12,
    ),
    doomed=st.lists(st.sampled_from(list("abcdef")), max_size=6),
)
def test_tp_u5_6_only_matching_rows_disappear(rows, doomed) -> None:
    mem = InMemoryTranslationRepository()
    mem.upsert_many([_t(k, s) for k, s in rows])
    removed = mem.purge(kind="rumor", ids=doomed)
    expected_gone = {(k, s) for k, s in rows if k == "rumor" and s in doomed}
    assert removed == len(expected_gone)
    remaining = {
        (t.source_kind, t.source_id) for t in _all(mem, [(k, s, "statement") for k, s in rows])
    }
    assert remaining == set(rows) - expected_gone


class _Item(BaseModel):
    id: str
    statement: str


class _LLM:
    def __init__(self) -> None:
        self.calls = 0

    def complete(self, prompt, *, system=None):
        self.calls += 1
        return "KO:" + prompt.split("Text:\n", 1)[-1]

    def structured(self, prompt, schema, *, system=None):  # pragma: no cover
        raise NotImplementedError


def test_service_purge_forgets_in_flight_keys() -> None:
    scheduled: list = []
    llm = _LLM()
    svc = TranslationService(
        InMemoryTranslationRepository(), Translator(llm), warm_scheduler=scheduled.append
    )
    svc.enrich([_Item(id="r1", statement="hi")], kind="rumor", fields=["statement"])
    assert len(scheduled) == 1  # one warm queued, key in flight
    svc.enrich([_Item(id="r1", statement="hi")], kind="rumor", fields=["statement"])
    assert len(scheduled) == 1  # in-flight suppression (U1 review #5)
    assert svc.purge(kind="rumor", ids=["r1"]) == 0
    svc.enrich([_Item(id="r1", statement="hi")], kind="rumor", fields=["statement"])
    assert len(scheduled) == 2  # forgotten: a later read may warm afresh


def test_enrichment_for_never_asks_for_the_source_language() -> None:
    """BR-U5-19: ?lang=en needs no translation — no rows, no warm."""
    from api.schemas import SOURCE_LANG, enrichment_for

    class _Loc:
        def __init__(self) -> None:
            self.translations = TranslationService(
                InMemoryTranslationRepository(), Translator(_LLM())
            )

    loc = _Loc()
    items = [_Item(id="r1", statement="hello")]
    assert SOURCE_LANG == "en"
    assert enrichment_for(loc, items, kind="rumor", fields=["statement"], lang="en") == {}  # type: ignore[arg-type]
    assert loc.translations._translator._llm.calls == 0
    enrichment_for(loc, items, kind="rumor", fields=["statement"], lang="ko")  # type: ignore[arg-type]
    assert loc.translations._translator._llm.calls == 1  # the ko path still warms


def test_review_6_a_world_purge_leaves_other_warm_ups_in_flight() -> None:
    """Review U5 #6: in-flight keys carry no world, so a world-scoped purge must not
    forget them — otherwise another world's item is translated twice."""
    scheduled: list = []
    svc = TranslationService(
        InMemoryTranslationRepository(), Translator(_LLM()), warm_scheduler=scheduled.append
    )
    item = [_Item(id="k-w2", statement="hi")]
    svc.enrich(item, kind="knowledge", fields=["statement"], world_id="w2")
    assert len(scheduled) == 1
    svc.purge(kind="knowledge", world_id="w1")
    svc.enrich(item, kind="knowledge", fields=["statement"], world_id="w2")
    assert len(scheduled) == 1  # still in flight: no second warm
