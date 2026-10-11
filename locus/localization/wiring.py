"""localization boundary composition: ``assemble_localization(shared) -> LocalizationContainer``.

Disabled (``TRANSLATION_ENABLED=false``) or without a SQL engine, the container
carries ``translations=None`` and the API layer shows originals. Without an LLM the
service still exists but has no translator: it reads the cache and seeds a demo's
translations, and never warms (V3, BR-V3-02). A keyless server therefore also creates
the ``translations`` table at start-up (code plan memo R-05).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from locus.localization.ports import TranslationStore
from locus.localization.service import TranslationService
from locus.localization.storage.postgres_repo import PostgresTranslationRepository
from locus.localization.translator import Translator
from locus.shared.wiring import SharedContainer


@dataclass
class LocalizationContainer:
    translations: TranslationService | None
    executor: ThreadPoolExecutor | None = None

    def close(self) -> None:
        if self.executor is not None:
            self.executor.shutdown(wait=False, cancel_futures=True)
            self.executor = None


def assemble_localization(
    shared: SharedContainer, *, store: TranslationStore | None = None
) -> LocalizationContainer:
    s = shared.settings
    if not s.translation_enabled:
        return LocalizationContainer(translations=None)
    if store is None:
        if shared.sql_engine is None:
            return LocalizationContainer(translations=None)
        pg = PostgresTranslationRepository(engine=shared.sql_engine)
        pg.ensure_schema()
        store = pg
    if shared.llm is None:  # V3: cache reads and seeding only, no warm and no pool
        return LocalizationContainer(
            translations=TranslationService(store, None, default_lang=s.translation_target_lang)
        )
    pool = ThreadPoolExecutor(max_workers=s.translation_warm_workers, thread_name_prefix="xlate")
    service = TranslationService(
        store,
        Translator(shared.llm),
        default_lang=s.translation_target_lang,
        warm_scheduler=pool.submit,
    )
    return LocalizationContainer(translations=service, executor=pool)
