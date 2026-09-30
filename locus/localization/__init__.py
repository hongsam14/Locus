"""localization — display-language translation cache (FR-G).

Owns the ``translations`` table and the cache-first ``TranslationService``.
Depends only on ``shared``; used by the API layer to decorate responses.
"""

from __future__ import annotations

from locus.localization.models import Translation
from locus.localization.ports import TranslationKey, TranslationStore
from locus.localization.service import Enrichment, TranslationService, source_hash
from locus.localization.storage.memory_repo import InMemoryTranslationRepository
from locus.localization.storage.postgres_repo import PostgresTranslationRepository
from locus.localization.translator import Translator
from locus.localization.wiring import LocalizationContainer, assemble_localization

__all__ = [
    "Translation",
    "TranslationKey",
    "TranslationStore",
    "Enrichment",
    "TranslationService",
    "source_hash",
    "InMemoryTranslationRepository",
    "PostgresTranslationRepository",
    "Translator",
    "LocalizationContainer",
    "assemble_localization",
]
