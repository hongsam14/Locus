"""ProviderFactory: select LLM/VLM/Embedding implementations from settings.

Default provider is OpenAI (Q7=D, default OpenAI). Adding a new provider means
adding a branch here + an adapter module — core code is unaffected.
"""

from __future__ import annotations

from ..config import Settings, get_settings
from .base import EmbeddingProvider, LLMProvider, VLMProvider


class ProviderFactory:
    """Builds provider instances based on configuration."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _require_openai_key(self) -> str:
        key = self._settings.openai_api_key
        if key is None:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Configure it in .env or the environment."
            )
        return key.get_secret_value()

    def llm(self) -> LLMProvider:
        provider = self._settings.llm_provider.lower()
        if provider == "openai":
            from .openai_provider import OpenAILLMProvider

            return OpenAILLMProvider(
                api_key=self._require_openai_key(),
                model=self._settings.openai_model_name,
                temperature=self._settings.llm_temperature,
            )
        raise ValueError(f"Unsupported llm_provider: {provider!r}")

    def vlm(self) -> VLMProvider:
        provider = self._settings.llm_provider.lower()
        if provider == "openai":
            from .openai_provider import OpenAIVLMProvider

            return OpenAIVLMProvider(
                api_key=self._require_openai_key(),
                model=self._settings.openai_vlm_model_name,
                temperature=self._settings.llm_temperature,
            )
        raise ValueError(f"Unsupported llm_provider: {provider!r}")

    def embedding(self) -> EmbeddingProvider:
        provider = self._settings.llm_provider.lower()
        if provider == "openai":
            from .openai_provider import OpenAIEmbeddingProvider

            return OpenAIEmbeddingProvider(
                api_key=self._require_openai_key(),
                model=self._settings.embedding_model,
                dimension=self._settings.embedding_dimension,
            )
        raise ValueError(f"Unsupported llm_provider: {provider!r}")
