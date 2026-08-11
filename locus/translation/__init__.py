"""Localization layer (UX Improvement / X1).

``Translator`` wraps the existing ``LLMProvider`` to translate text; the
``TranslationService`` adds a cache-first policy over the session-store
translation cache. Both are mockable for offline tests (NFR-UX3).
"""

from __future__ import annotations

from .service import TranslationService, source_hash
from .translator import Translator

__all__ = ["Translator", "TranslationService", "source_hash"]
