"""Translator — LLM-backed text translation (X1, C1).

Reuses the existing ``LLMProvider`` port (FR-UX3.3) so no separate translation
service or key is needed and offline tests can mock it. Fail-safe (SEC-C): a
failed or blank translation yields ``None`` from :meth:`try_translate` so the
caller can distinguish a real translation (cache it, even if identical to the
source) from a failure (do not cache, retry later). BR-X1-1/3/4.
"""

from __future__ import annotations

import logging

from ..llm.base import LLMProvider

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a professional translator. Translate the user's text into the target "
    "language. Preserve meaning, tone, named entities and rough length. Do not add "
    "notes or quotation marks. Return only the translated text."
)


class Translator:
    """Translate text via an ``LLMProvider``. Deterministic offline via mocks."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def try_translate(self, text: str, target_lang: str = "ko") -> str | None:
        """Translate ``text`` into ``target_lang``.

        Returns the translated string on success (which may legitimately equal the
        source, e.g. proper nouns/numbers — the caller should still cache it),
        ``None`` for blank input or any LLM failure (do not cache; retry later).
        """
        if not text or not text.strip():
            return None
        try:
            out = self._llm.complete(self._prompt(text, target_lang), system=_SYSTEM)
        except Exception:  # SEC-C: never propagate; log and signal failure
            logger.warning("translation failed; will retry later", exc_info=True)
            return None
        out = (out or "").strip()
        return out or None

    @staticmethod
    def _prompt(text: str, target_lang: str) -> str:
        return f"Target language: {target_lang}\n\nText:\n{text}"
