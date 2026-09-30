"""localization persistence port (FR-G1): ``TranslationStore``.

Keys are ``(source_kind, source_id, source_field)``; ``target_lang`` is passed
separately. Names follow the design (component-methods.md L2): ``get_many`` /
``upsert_many``; ``purge`` lands in U5.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from locus.localization.models import Translation

TranslationKey = tuple[str, str, str]  # (source_kind, source_id, source_field)


@runtime_checkable
class TranslationStore(Protocol):
    def get_many(
        self, keys: list[TranslationKey], target_lang: str
    ) -> dict[tuple[str, str], Translation]: ...  # -> {(source_id, source_field): Translation}
    def upsert_many(self, translations: list[Translation]) -> list[Translation]: ...
