"""LLMCallCounter — per-build accounting of LLM / VLM / embedding calls (U2 BR-U2-15, NFR-5).

``WorldBuilder.build`` creates one counter per build, wraps the providers it was
given and hands the wrappers to every factory, so ``BuildReport.llm_calls`` and
``embedding_calls`` count exactly that build's calls (no shared state).
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from locus.shared.llm.base import EmbeddingProvider, LLMProvider, VLMProvider

TModel = TypeVar("TModel", bound=BaseModel)


class LLMCallCounter:
    def __init__(self) -> None:
        self.llm_calls = 0  # LLM completions/structured + VLM image analyses
        self.embedding_calls = 0  # embed() batches

    def wrap_llm(self, llm: LLMProvider | None) -> LLMProvider | None:
        return None if llm is None else _CountingLLM(llm, self)

    def wrap_vlm(self, vlm: VLMProvider | None) -> VLMProvider | None:
        return None if vlm is None else _CountingVLM(vlm, self)

    def wrap_embedding(self, embedding: EmbeddingProvider | None) -> EmbeddingProvider | None:
        return None if embedding is None else _CountingEmbedding(embedding, self)


class _CountingLLM:
    def __init__(self, inner: LLMProvider, counter: LLMCallCounter) -> None:
        self._inner, self._counter = inner, counter

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        self._counter.llm_calls += 1
        return self._inner.complete(prompt, system=system)

    def structured(self, prompt: str, schema: type[TModel], *, system: str | None = None) -> TModel:
        self._counter.llm_calls += 1
        return self._inner.structured(prompt, schema, system=system)


class _CountingVLM:
    def __init__(self, inner: VLMProvider, counter: LLMCallCounter) -> None:
        self._inner, self._counter = inner, counter

    def analyze_image(self, image: bytes, prompt: str, *, system: str | None = None) -> str:
        self._counter.llm_calls += 1
        return self._inner.analyze_image(image, prompt, system=system)


class _CountingEmbedding:
    def __init__(self, inner: EmbeddingProvider, counter: LLMCallCounter) -> None:
        self._inner, self._counter = inner, counter

    @property
    def dimension(self) -> int:
        return self._inner.dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._counter.embedding_calls += 1
        return self._inner.embed(texts)
