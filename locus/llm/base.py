"""Provider-abstraction ports for LLM / VLM / Embedding (NFR-B, AD-Q4=C).

Core modules depend ONLY on these Protocols; concrete adapters (OpenAI via
LangChain) live behind ``ProviderFactory``. This keeps the system provider-
agnostic and easy to mock in tests.
"""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

TModel = TypeVar("TModel", bound=BaseModel)


@runtime_checkable
class LLMProvider(Protocol):
    """Text completion + structured extraction."""

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        """Return a free-text completion for ``prompt``."""
        ...

    def structured(self, prompt: str, schema: type[TModel], *, system: str | None = None) -> TModel:
        """Return an instance of ``schema`` parsed from the model output."""
        ...


@runtime_checkable
class VLMProvider(Protocol):
    """Vision-language analysis (e.g. map image -> terrain/region text)."""

    def analyze_image(self, image: bytes, prompt: str, *, system: str | None = None) -> str:
        """Return a text analysis of ``image`` guided by ``prompt``."""
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Text embedding for semantic search."""

    @property
    def dimension(self) -> int:
        """Output vector dimension."""
        ...

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...
