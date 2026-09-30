"""In-memory ``TranslationStore`` — offline tests / mock."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

from locus.localization.models import Translation


class InMemoryTranslationRepository:
    def __init__(self) -> None:
        # (kind, source_id, field, lang) -> Translation
        self._translations: dict[tuple[str, str, str, str], Translation] = {}
        self._clock = 0

    def _now(self) -> datetime:
        # Strictly increasing fake server time for deterministic ordering.
        self._clock += 1
        return datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=self._clock)

    # -- port ------------------------------------------------------------- #

    def get_many(
        self, keys: list[tuple[str, str, str]], target_lang: str
    ) -> dict[tuple[str, str], Translation]:
        out: dict[tuple[str, str], Translation] = {}
        for kind, source_id, field in keys:
            t = self._translations.get((kind, source_id, field, target_lang))
            if t is not None:
                out[(source_id, field)] = deepcopy(t)
        return out

    def _upsert_one(self, translation: Translation) -> Translation:
        key = (
            translation.source_kind,
            translation.source_id,
            translation.source_field,
            translation.target_lang,
        )
        stored = deepcopy(translation)
        existing = self._translations.get(key)
        if existing is not None:  # same semantics as ON CONFLICT: the row keeps its id
            stored.id = existing.id
            stored.created_at = existing.created_at
        if stored.created_at is None:
            stored.created_at = self._now()
        self._translations[key] = stored
        return deepcopy(stored)

    def upsert_many(self, translations: list[Translation]) -> list[Translation]:
        return [self._upsert_one(t) for t in translations]
