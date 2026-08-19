"""TranslationService — cache-first localization (X1, C3).

Read paths are LLM-free (P-F review #3): :meth:`enrich` fills ``*_ko`` fields
from the cache only and never blocks on the LLM. Cache misses are handed to a
``warm_scheduler`` (a background thread in production; inline when none is set)
which translates and batch-writes them, so a later read serves them from cache
(eventually consistent). Cache hit requires the stored ``source_hash`` to match
the current text, so edited sources are re-translated (FR-UX3.5 / BR-X1-6). A
successful translation is cached even when identical to the source; only real
failures are left uncached to retry (review #4). Both the rumor/event list
endpoints and the region-knowledge query call :meth:`enrich`, so the enrichment
idiom lives in one place (review #10).
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable

from ..session.models import Translation
from ..session.repository import SessionRepository
from .translator import Translator

logger = logging.getLogger(__name__)

# (text_attr, ko_attr) pairs to localize on an item.
FieldSpec = tuple[str, str]


def source_hash(text: str) -> str:
    """Stable hash of the source text (whitespace-normalized). BR-X1-6."""
    normalized = (text or "").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class TranslationService:
    """Cache-first, read-non-blocking translation over the session store."""

    def __init__(
        self,
        repo: SessionRepository,
        translator: Translator,
        *,
        default_lang: str = "ko",
        warm_scheduler: Callable[[Callable[[], None]], None] | None = None,
    ) -> None:
        self._repo = repo
        self._translator = translator
        self._lang = default_lang
        # None -> run warming inline (tests/simple deployments); production passes a
        # thread-pool submit so reads never block on the LLM (review #3).
        self._schedule = warm_scheduler or (lambda fn: fn())

    def enrich(
        self,
        items: list,
        *,
        kind: str,
        fields: list[FieldSpec],
        id_attr: str = "id",
        world_id: str | None = None,
        session_id: str | None = None,
        lang: str | None = None,
    ) -> list:
        """Fill each item's ``ko_attr`` from cache (LLM-free); schedule misses to
        warm in the background. Never raises — a cache/DB error degrades to
        originals (review #1). Returns ``items`` for convenience."""
        lang = lang or self._lang
        if not items:
            return items
        specs: list[tuple[object, str, str, str, str]] = []  # (item, id, text_attr, ko_attr, text)
        for it in items:
            item_id = getattr(it, id_attr)
            for text_attr, ko_attr in fields:
                text = getattr(it, text_attr, None)
                if text and text.strip():
                    specs.append((it, item_id, text_attr, ko_attr, text))
        if not specs:
            return items

        keyed = [(kind, sid, field, text) for _it, sid, field, _ko, text in specs]
        cache = self._cached(keyed, lang)  # fail-safe -> {} on error
        misses: list[tuple[str, str, str, str]] = []
        for it, sid, text_attr, ko_attr, text in specs:
            ko = cache.get((sid, text_attr))
            if ko is not None:
                setattr(it, ko_attr, ko)
            else:
                misses.append((kind, sid, text_attr, text))
        if misses:
            self._schedule(
                lambda m=misses: self._warm(m, world_id=world_id, session_id=session_id, lang=lang)
            )
        return items

    # -- internals -------------------------------------------------------- #
    def _cached(self, triples: list[tuple[str, str, str, str]], lang: str) -> dict:
        """Cache-only lookup: {(id, field): ko} for rows whose stored hash matches
        the current text. Swallows repo errors (translation is a display nicety)."""
        keys = [(kind, sid, field) for kind, sid, field, _text in triples]
        try:
            rows = self._repo.get_translations_many(keys, lang)
        except Exception:
            logger.warning("translation cache read failed; showing originals", exc_info=True)
            return {}
        out: dict[tuple[str, str], str] = {}
        for _kind, sid, field, text in triples:
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
        """Translate misses and batch-write them (review #8). Best-effort — runs on
        the warm scheduler (background thread in prod, review #3)."""
        rows: list[Translation] = []
        for kind, sid, field, text in misses:
            ko = self._translator.try_translate(text, lang)
            if ko is None:  # failure/blank -> leave uncached to retry (review #4)
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
            self._repo.upsert_translations(rows)
        except Exception:
            logger.warning("translation cache write failed", exc_info=True)
