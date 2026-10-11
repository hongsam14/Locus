"""TranslationService — cache-first localization (FR-G1/G2).

Read paths are LLM-free: :meth:`enrich` looks up the cache only and never blocks
on the LLM. Cache misses are handed to a ``warm_scheduler`` (a background thread
in production; inline when none is set) which translates and batch-writes them,
so a later read serves them from cache (eventually consistent). A cache hit
requires the stored ``source_hash`` to match the current text, so edited sources
are re-translated (BR-X1-6). A successful translation is cached even when
identical to the source; only real failures are left uncached to retry.

``enrich`` **returns a mapping** and never mutates the domain objects it is
given (FR-A2: domain models carry no ``*_ko`` fields; the API layer copies the
mapping into response DTOs).

V3: the service also runs **without a translator** (no LLM key): it then reads the
cache, seeds hand-made translations (:meth:`seed`, a demo's translation file) and
carries a row to a new key (:meth:`carry`), but never warms a miss (BR-V3-02).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Mapping, Sequence
from functools import partial
from typing import Any

from locus.localization.models import SeedReport, Translation
from locus.localization.ports import TranslationKey, TranslationStore
from locus.localization.translator import Translator
from locus.shared.models.i18n import (
    TranslationEntry,
    source_hash,  # moved to shared (V3); re-exported here
)

logger = logging.getLogger(__name__)

# {item_id: {field: translated_text}}
Enrichment = dict[str, dict[str, str]]
# Accepts a thunk and runs it now or later (e.g. ThreadPoolExecutor.submit).
WarmScheduler = Callable[[Callable[[], None]], Any]


def _run_inline(fn: Callable[[], None]) -> None:
    fn()


class TranslationService:
    """Cache-first, read-non-blocking translation over a ``TranslationStore``."""

    def __init__(
        self,
        store: TranslationStore,
        translator: Translator | None,
        *,
        default_lang: str = "ko",
        warm_scheduler: WarmScheduler | None = None,
    ) -> None:
        self._store = store
        self._translator = translator
        self._lang = default_lang
        # None -> run warming inline (tests/simple deployments); production passes a
        # thread-pool submit so reads never block on the LLM.
        self._schedule: WarmScheduler = warm_scheduler or _run_inline
        # keys currently being translated — a second read of the same miss does
        # not schedule a second LLM call (review U1 #5)
        self._in_flight: set[tuple[str, str, str, str]] = set()
        self._in_flight_lock = threading.Lock()

    @property
    def default_lang(self) -> str:
        return self._lang

    def enrich(
        self,
        items: Sequence[Any],
        *,
        kind: str,
        fields: Sequence[str],
        id_attr: str = "id",
        world_id: str | None = None,
        session_id: str | None = None,
        lang: str | None = None,
    ) -> Enrichment:
        """Return ``{item_id: {field: translation}}`` for cached translations of
        ``fields`` on each item (LLM-free); schedule misses to warm in the
        background. Never raises — a cache/DB error degrades to an empty mapping."""
        lang = lang or self._lang
        out: Enrichment = {}
        if not items:
            return out
        warm = self._translator is not None  # without an LLM a miss just stays the original
        specs: list[tuple[str, str, str]] = []  # (item_id, field, text)
        for it in items:
            item_id = str(getattr(it, id_attr))
            for field in fields:
                text = getattr(it, field, None)
                if text and str(text).strip():
                    specs.append((item_id, field, str(text)))
        if not specs:
            return out

        cache = self._cached([(kind, sid, field, text) for sid, field, text in specs], lang)
        misses: list[tuple[str, str, str, str]] = []
        for sid, field, text in specs:
            ko = cache.get((sid, field))
            if ko is not None:
                out.setdefault(sid, {})[field] = ko
            else:
                misses.append((kind, sid, field, text))
        if misses and warm:
            with self._in_flight_lock:
                fresh = [m for m in misses if (*m[:3], lang) not in self._in_flight]
                self._in_flight.update((*m[:3], lang) for m in fresh)
            if fresh:
                try:
                    self._schedule(
                        partial(
                            self._warm, fresh, world_id=world_id, session_id=session_id, lang=lang
                        )
                    )
                except Exception:  # e.g. executor already shut down — reads stay LLM-free
                    logger.warning("translation warm could not be scheduled", exc_info=True)
                    self._release(fresh, lang)
        return out

    def purge(
        self,
        *,
        kind: str | None = None,
        ids: list[str] | None = None,
        world_id: str | None = None,
        session_id: str | None = None,
    ) -> int:
        """Drop cached translations whose source is gone (U5, FR-G4, BR-U5-22/33).

        Also forgets matching in-flight keys so a later read can warm afresh. A warm
        already running may still write one row back after this — an orphan cache row
        with no effect on reads (only live sources are looked up); the next purge
        removes it. Only an **id-scoped** purge touches in-flight keys: they carry no
        world or session, so a world/session/kind-only purge would forget every other
        world's warm-ups too and translate them twice (review U5 #6). Leaving them is
        the same harmless race.
        """
        removed = self._store.purge(kind=kind, ids=ids, world_id=world_id, session_id=session_id)
        if ids is not None:
            wanted = set(ids)
            with self._in_flight_lock:
                self._in_flight = {
                    key
                    for key in self._in_flight
                    if not ((kind is None or key[0] == kind) and key[1] in wanted)
                }
        return removed

    def prune_world(self, world_id: str, keep_ids: set[str]) -> int:
        """After a world replace: drop the world's rows whose source id the new world
        lacks, keep the rest — the source hash already decides whether a kept row is
        still shown (V3, BR-V3-13 as corrected by code review 01 #1)."""
        return self._store.purge_world_except(world_id, keep_ids)

    def seed(
        self,
        entries: Sequence[TranslationEntry],
        *,
        lang: str,
        current_text: Mapping[tuple[str, str, str], str],
        world_id: str,
    ) -> SeedReport:
        """Put hand-made translations in the cache (V3, FD BLM § 3, BR-V3-15).

        An entry is kept only while its source hashes like the text the world holds now
        (``current_text[(kind, id, field)]``); otherwise it is ``stale``, and an entry
        whose key the world does not hold is ``unknown``. Kept rows carry ``world_id`` so
        a world replace drops them, and overwrite an existing row of the same key (a
        later duplicate in ``entries`` wins). The keys leave the in-flight set; a warm
        already running may still finish after this and write its own text (code plan
        memo R-04). A store failure is logged and reported as nothing seeded.
        """
        stale = unknown = 0
        rows: dict[tuple[str, str, str], Translation] = {}
        for entry in entries:
            now = current_text.get(entry.key)
            if now is None or not now.strip():
                unknown += 1
                continue
            if entry.source_hash != source_hash(now):
                stale += 1
                continue
            rows[entry.key] = Translation(
                source_kind=entry.kind,
                source_id=entry.id,
                source_field=entry.field,
                target_lang=lang,
                text=entry.text,
                source_hash=source_hash(now),
                world_id=world_id,
            )
        if not rows:
            return SeedReport(stale=stale, unknown=unknown)
        with self._in_flight_lock:
            self._in_flight.difference_update((*key, lang) for key in rows)
        try:
            self._store.upsert_many(list(rows.values()))
        except Exception:
            logger.warning("translation seeding failed (world %s)", world_id, exc_info=True)
            return SeedReport(stale=stale, unknown=unknown)
        return SeedReport(seeded=len(rows), stale=stale, unknown=unknown)

    def carry(
        self,
        sources: Sequence[TranslationKey],
        target: TranslationKey,
        *,
        text: str,
        langs: Sequence[str],
        session_id: str | None = None,
    ) -> int:
        """Copy a translation to a new key — no LLM (V3, BR-V3-17). For each language
        the first source row whose hash matches ``text`` is written under ``target``;
        a language with no matching row is left alone. Returns the rows written.
        Store errors propagate; the caller decides what a failure means."""
        if not sources or not text.strip():
            return 0
        want = source_hash(text)
        kind, target_id, target_field = target
        rows: list[Translation] = []
        for lang in langs:
            found = self._store.get_many(list(sources), lang)
            for _kind, source_id, source_field in sources:
                row = found.get((source_id, source_field))
                if row is not None and row.source_hash == want:
                    rows.append(
                        Translation(
                            source_kind=kind,
                            source_id=target_id,
                            source_field=target_field,
                            target_lang=lang,
                            text=row.text,
                            source_hash=want,
                            session_id=session_id,
                        )
                    )
                    break
        if rows:
            self._store.upsert_many(rows)
        return len(rows)

    def _release(self, misses: list[tuple[str, str, str, str]], lang: str) -> None:
        with self._in_flight_lock:
            self._in_flight.difference_update((*m[:3], lang) for m in misses)

    # -- internals -------------------------------------------------------- #
    def _cached(self, quads: list[tuple[str, str, str, str]], lang: str) -> dict:
        """Cache-only lookup: {(id, field): text} for rows whose stored hash matches
        the current text. Swallows store errors (translation is a display nicety)."""
        keys: list[TranslationKey] = [(kind, sid, field) for kind, sid, field, _text in quads]
        try:
            rows = self._store.get_many(keys, lang)
        except Exception:
            logger.warning("translation cache read failed; showing originals", exc_info=True)
            return {}
        out: dict[tuple[str, str], str] = {}
        for _kind, sid, field, text in quads:
            row = rows.get((sid, field))
            if row is not None and row.source_hash == source_hash(text):
                out[(sid, field)] = row.text
        return out

    def _warm(
        self,
        misses: list[tuple[str, str, str, str]],
        *,
        world_id: str | None,
        session_id: str | None,
        lang: str,
    ) -> None:
        """Translate misses and batch-write them. Best-effort — runs on the warm
        scheduler (background thread in prod)."""
        try:
            self._warm_inner(misses, world_id=world_id, session_id=session_id, lang=lang)
        finally:
            self._release(misses, lang)

    def _warm_inner(
        self,
        misses: list[tuple[str, str, str, str]],
        *,
        world_id: str | None,
        session_id: str | None,
        lang: str,
    ) -> None:
        rows: list[Translation] = []
        if self._translator is None:  # enrich never schedules without one
            return
        for kind, sid, field, text in misses:
            ko = self._translator.try_translate(text, lang)
            if ko is None:  # failure/blank -> leave uncached to retry
                continue
            rows.append(
                Translation(
                    source_kind=kind,
                    source_id=sid,
                    source_field=field,
                    target_lang=lang,
                    text=ko,  # cached even if ko == text (successful no-op translation)
                    source_hash=source_hash(text),
                    world_id=world_id,
                    session_id=session_id,
                )
            )
        if not rows:
            return
        try:
            self._store.upsert_many(rows)
        except Exception:
            logger.warning("translation cache write failed", exc_info=True)
