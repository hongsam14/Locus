"""V3: the translation service without an LLM, seeding a demo's translations and carrying
a row to a new key (FD BLM § 2·3·10, BR-V3-01·02·04·15·17, TP-V3-2·6, code plan R-04/R-05/R-08)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from locus.localization import (
    InMemoryTranslationRepository,
    SeedReport,
    TranslationService,
    Translator,
    assemble_localization,
    source_hash,
)
from locus.shared.config.settings import Settings
from locus.shared.models import TranslationEntry


class _Region(BaseModel):
    id: str
    name: str


def _entry(id_: str, source: str, text: str, field: str = "name") -> TranslationEntry:
    return TranslationEntry(kind="region", id=id_, field=field, source=source, text=text)


def _shared(*, llm=None, enabled: bool = True, engine: object | None = object()):
    settings = Settings.model_construct(translation_enabled=enabled)
    return SimpleNamespace(settings=settings, sql_engine=engine, llm=llm)


class _LLM:
    calls = 0

    def complete(self, prompt, *, system=None):
        self.calls += 1
        return "KO"

    def structured(self, prompt, schema, *, system=None):  # pragma: no cover
        raise NotImplementedError


# --- assemble (TP-V3-6, code plan memo R-05) ------------------------------------ #
def test_without_an_llm_there_is_a_service_that_never_warms() -> None:
    store = InMemoryTranslationRepository()
    loc = assemble_localization(_shared(llm=None), store=store)  # type: ignore[arg-type]
    svc = loc.translations
    assert svc is not None and loc.executor is None
    region = _Region(id="region-saltwake", name="Saltwake Harbor")
    assert svc.enrich([region], kind="region", fields=["name"], world_id="w") == {}
    assert svc._in_flight == set()  # nothing was scheduled  # noqa: SLF001
    svc.seed(
        [_entry("region-saltwake", "Saltwake Harbor", "솔트웨이크 항구")],
        lang="ko",
        current_text={("region", "region-saltwake", "name"): "Saltwake Harbor"},
        world_id="w",
    )
    assert svc.enrich([region], kind="region", fields=["name"], world_id="w") == {
        "region-saltwake": {"name": "솔트웨이크 항구"}
    }
    loc.close()


def test_without_a_translator_the_scheduler_is_never_called() -> None:  # review 01 #4
    asked: list = []
    svc = TranslationService(InMemoryTranslationRepository(), None, warm_scheduler=asked.append)
    svc.enrich([_Region(id="r1", name="Ironcrag")], kind="region", fields=["name"], world_id="w")
    assert asked == []


def test_off_or_without_a_database_there_is_no_service() -> None:
    store = InMemoryTranslationRepository()
    assert assemble_localization(_shared(enabled=False), store=store).translations is None  # type: ignore[arg-type]
    assert assemble_localization(_shared(engine=None)).translations is None  # type: ignore[arg-type]


def test_with_an_llm_a_miss_is_still_scheduled() -> None:  # code plan memo R-08 (c)
    scheduled: list = []
    svc = TranslationService(
        InMemoryTranslationRepository(), Translator(_LLM()), warm_scheduler=scheduled.append
    )
    svc.enrich([_Region(id="r1", name="Ironcrag")], kind="region", fields=["name"], world_id="w")
    assert len(scheduled) == 1


# --- seed (BR-V3-01·04·15, TP-V3-2) -------------------------------------------- #
def _seeded(entries, current, store=None):
    store = store or InMemoryTranslationRepository()
    svc = TranslationService(store, None)
    return svc.seed(entries, lang="ko", current_text=current, world_id="w"), svc, store


def test_seed_keeps_only_entries_whose_source_is_the_text_now() -> None:
    current = {
        ("region", "a", "name"): "Saltwake Harbor",
        ("region", "b", "name"): "Ironcrag",
        ("region", "c", "name"): "   ",  # blank: not a translation target
    }
    report, svc, store = _seeded(
        [
            _entry("a", "  Saltwake Harbor ", "솔트웨이크 항구"),  # ends differ only: kept
            _entry("b", "Iron Crag", "아이언 크래그"),  # source changed since: stale
            _entry("c", "x", "y"),  # blank now: unknown
            _entry("z", "Nowhere", "어디에도"),  # not in this world: unknown
        ],
        current,
    )
    assert report == SeedReport(seeded=1, stale=1, unknown=2)
    row = store.get_many([("region", "a", "name")], "ko")[("a", "name")]
    assert row.world_id == "w" and row.source_hash == source_hash("Saltwake Harbor")
    assert svc.enrich([_Region(id="b", name="Ironcrag")], kind="region", fields=["name"]) == {}


def test_seeding_again_overwrites_and_adds_no_rows() -> None:
    current = {("region", "a", "name"): "Saltwake Harbor"}
    store = InMemoryTranslationRepository()
    _seeded([_entry("a", "Saltwake Harbor", "첫 번역")], current, store)
    report, _, _ = _seeded(
        [_entry("a", "Saltwake Harbor", "둘째"), _entry("a", "Saltwake Harbor", "솔트웨이크 항구")],
        current,
        store,
    )
    assert report.seeded == 1  # a later duplicate wins, one row
    assert len(store._translations) == 1  # noqa: SLF001
    assert store.get_many([("region", "a", "name")], "ko")[("a", "name")].text == "솔트웨이크 항구"


def test_seeding_forgets_in_flight_keys() -> None:  # code plan memo R-04
    svc = TranslationService(InMemoryTranslationRepository(), None)
    svc._in_flight.add(("region", "a", "name", "ko"))  # noqa: SLF001
    svc.seed(
        [_entry("a", "Ironcrag", "아이언크래그")],
        lang="ko",
        current_text={("region", "a", "name"): "Ironcrag"},
        world_id="w",
    )
    assert svc._in_flight == set()  # noqa: SLF001


class _BrokenStore(InMemoryTranslationRepository):
    def upsert_many(self, translations):
        raise RuntimeError("database down")


def test_a_store_failure_seeds_nothing_and_does_not_raise() -> None:
    report, _, _ = _seeded(
        [_entry("a", "Ironcrag", "아이언크래그")],
        {("region", "a", "name"): "Ironcrag"},
        _BrokenStore(),
    )
    assert report == SeedReport(seeded=0)


# --- carry (BR-V3-17) ------------------------------------------------------------ #
def _seed_rows(store, *rows: tuple[str, str, str]) -> None:
    svc = TranslationService(store, None)
    current = {}
    entries = []
    for field, source, text in rows:
        current[("event_seed", "seed-1", field)] = source
        entries.append(
            TranslationEntry(kind="event_seed", id="seed-1", field=field, source=source, text=text)
        )
    svc.seed(entries, lang="ko", current_text=current, world_id="w")


SOURCES = [("event_seed", "seed-1", "description"), ("event_seed", "seed-1", "title")]


def test_carry_copies_the_row_whose_hash_matches_the_new_text() -> None:
    store = InMemoryTranslationRepository()
    _seed_rows(
        store, ("title", "Blight", "마름병"), ("description", "Mushrooms rot.", "버섯이 썩는다.")
    )
    svc = TranslationService(store, None)
    n = svc.carry(
        SOURCES,
        ("event", "ev-1", "description"),
        text="Mushrooms rot.",
        langs=["ko"],
        session_id="s1",
    )
    assert n == 1
    row = store.get_many([("event", "ev-1", "description")], "ko")[("ev-1", "description")]
    assert row.text == "버섯이 썩는다." and row.session_id == "s1" and row.world_id is None
    # a seed with no description starts its event with the title
    assert svc.carry(SOURCES, ("event", "ev-2", "description"), text="Blight", langs=["ko"]) == 1


def test_carry_writes_nothing_when_no_source_matches() -> None:
    store = InMemoryTranslationRepository()
    _seed_rows(store, ("description", "Mushrooms rot.", "버섯이 썩는다."))
    svc = TranslationService(store, None)
    assert (
        svc.carry(SOURCES, ("event", "ev-1", "description"), text="Edited since.", langs=["ko"])
        == 0
    )
    assert (
        svc.carry(SOURCES, ("event", "ev-1", "description"), text="Mushrooms rot.", langs=["ja"])
        == 0
    )
    assert svc.carry([], ("event", "ev-1", "description"), text="x", langs=["ko"]) == 0


def test_carry_lets_a_store_error_through() -> None:  # the api helper decides (code plan R-07)
    class _Down(InMemoryTranslationRepository):
        def get_many(self, keys, target_lang):
            raise RuntimeError("database down")

    with pytest.raises(RuntimeError):
        TranslationService(_Down(), None).carry(
            SOURCES, ("event", "e", "description"), text="x", langs=["ko"]
        )
