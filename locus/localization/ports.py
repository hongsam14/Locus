"""localization persistence port (FR-G1): ``TranslationStore``.

Keys are ``(source_kind, source_id, source_field)``; ``target_lang`` is passed
separately. Names follow the design (component-methods.md L2): ``get_many`` /
``upsert_many``; ``purge`` (U5) removes rows whose source is gone.
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
    def purge(
        self,
        *,
        kind: str | None = None,
        ids: list[str] | None = None,
        world_id: str | None = None,
        session_id: str | None = None,
    ) -> int: ...  # U5 (FR-G4): rows removed; ValueError when no filter is given
