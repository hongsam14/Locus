"""OpenAI implementations of the provider ports, via LangChain (AD-Q4=C).

LangChain packages are imported lazily so that importing this module (e.g. from
the factory) does not require the optional dependency until a provider is
actually instantiated. Tests mock the providers rather than calling OpenAI.
"""

from __future__ import annotations

import base64
from typing import TypeVar

from pydantic import BaseModel

from .base import EmbeddingProvider, LLMProvider, VLMProvider
from .retry import CALL_TIMEOUT_SECONDS, with_retry

TModel = TypeVar("TModel", bound=BaseModel)


class OpenAILLMProvider(LLMProvider):
    """Chat completion + structured output backed by ChatOpenAI."""

    def __init__(self, *, api_key: str, model: str, temperature: float = 0.2) -> None:
        from langchain_openai import ChatOpenAI

        self._client = ChatOpenAI(
            api_key=api_key,
            model=model,
            temperature=temperature,
            timeout=CALL_TIMEOUT_SECONDS,
        )

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        messages = self._messages(prompt, system)

        @with_retry
        def _call() -> str:
            return str(self._client.invoke(messages).content)

        return _call()

    def structured(self, prompt: str, schema: type[TModel], *, system: str | None = None) -> TModel:
        messages = self._messages(prompt, system)
        structured_client = self._client.with_structured_output(schema)

        @with_retry
        def _call() -> TModel:
            return structured_client.invoke(messages)  # type: ignore[return-value]

        return _call()

    @staticmethod
    def _messages(prompt: str, system: str | None) -> list[tuple[str, str]]:
        msgs: list[tuple[str, str]] = []
        if system:
            msgs.append(("system", system))
        msgs.append(("human", prompt))
        return msgs


class OpenAIVLMProvider(VLMProvider):
    """Vision analysis backed by a multimodal ChatOpenAI model."""

    def __init__(self, *, api_key: str, model: str, temperature: float = 0.2) -> None:
        from langchain_openai import ChatOpenAI

        self._client = ChatOpenAI(
            api_key=api_key,
            model=model,
            temperature=temperature,
            timeout=CALL_TIMEOUT_SECONDS,
        )

    def analyze_image(self, image: bytes, prompt: str, *, system: str | None = None) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        b64 = base64.b64encode(image).decode("ascii")
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]
        messages: list = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=content))

        @with_retry
        def _call() -> str:
            return str(self._client.invoke(messages).content)

        return _call()


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Embeddings backed by OpenAIEmbeddings (default text-embedding-3-small)."""

    def __init__(self, *, api_key: str, model: str, dimension: int) -> None:
        from langchain_openai import OpenAIEmbeddings

        self._client = OpenAIEmbeddings(api_key=api_key, model=model)
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        @with_retry
        def _call() -> list[list[float]]:
            return self._client.embed_documents(texts)

        return _call()
