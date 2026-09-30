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
"""

from __future__ import annotations

import hashlib
import logging
import threading
from collections.abc import Callable, Sequence
from functools import partial
from typing import Any

from locus.localization.models import Translation
from locus.localization.ports import TranslationKey, TranslationStore
from locus.localization.translator import Translator

logger = logging.getLogger(__name__)

# {item_id: {field: translated_text}}
Enrichment = dict[str, dict[str, str]]
# Accepts a thunk and runs it now or later (e.g. ThreadPoolExecutor.submit).
WarmScheduler = Callable[[Callable[[], None]], Any]


def _run_inline(fn: Callable[[], None]) -> None:
    fn()


def source_hash(text: str) -> str:
    """Stable hash of the source text (whitespace-normalized). BR-X1-6."""
    normalized = (text or "").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class TranslationService:
    """Cache-first, read-non-blocking translation over a ``TranslationStore``."""

    def __init__(
        self,
        store: TranslationStore,
        translator: Translator,
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
        if misses:
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
        removes it. World/session-scoped purges cannot see in-flight keys (they carry
        no world or session), which is the same harmless race.
        """
        removed = self._store.purge(kind=kind, ids=ids, world_id=world_id, session_id=session_id)
        if kind is not None or ids is not None:
            wanted = set(ids) if ids is not None else None
            with self._in_flight_lock:
                self._in_flight = {
                    key
                    for key in self._in_flight
                    if not (
                        (kind is None or key[0] == kind) and (wanted is None or key[1] in wanted)
                    )
                }
        return removed

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
