"""WikiPriorLinker — build PRIOR_RELATED_TO edges among a world's priors (FR-IM2.3/2.4).

Embedding picks top-k candidate pairs (NFR-IM4 guard: no O(n^2) LLM calls, BR-A7);
the LLM judges each candidate's relation/weight. Links stay within one world
(BR-A6); ``cross_domain`` flags links whose endpoints share no domain.
"""

from __future__ import annotations

from ..llm.base import EmbeddingProvider, LLMProvider
from ..models import Provenance, SourceKind, WikiPrior, WikiPriorLink
from .schemas import PriorLinkVerdict


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


class WikiPriorLinker:
    def __init__(
        self,
        llm: LLMProvider,
        embedding: EmbeddingProvider | None = None,
        *,
        top_k: int = 5,
        weight_threshold: float = 0.3,
    ) -> None:
        self._llm = llm
        self._embedding = embedding
        self._top_k = top_k
        self._threshold = weight_threshold

    def link(self, priors: list[WikiPrior], *, world_id: str) -> list[WikiPriorLink]:
        if self._embedding is None or len(priors) < 2:
            return []  # graceful: candidates need embeddings (BR-A14)
        try:
            vectors = self._embedding.embed([self._text(p) for p in priors])
        except Exception:
            return []

        candidates = self._candidate_pairs(priors, vectors)
        links: list[WikiPriorLink] = []
        seen: set[tuple[str, str]] = set()
        for i, j in candidates:
            key = tuple(sorted((priors[i].id, priors[j].id)))
            if key in seen:
                continue
            seen.add(key)
            link = self._judge(priors[i], priors[j], world_id=world_id)
            if link is not None:
                links.append(link)
        return links

    # -- internals -------------------------------------------------------- #
    def _candidate_pairs(
        self, priors: list[WikiPrior], vectors: list[list[float]]
    ) -> list[tuple[int, int]]:
        """Top-k most-similar partner for each prior (embedding gate, BR-A7)."""
        pairs: set[tuple[int, int]] = set()
        for i in range(len(priors)):
            sims = sorted(
                ((_cosine(vectors[i], vectors[j]), j) for j in range(len(priors)) if j != i),
                reverse=True,
            )
            for _score, j in sims[: self._top_k]:
                pairs.add((min(i, j), max(i, j)))
        return sorted(pairs)

    def _judge(self, a: WikiPrior, b: WikiPrior, *, world_id: str) -> WikiPriorLink | None:
        try:
            verdict = self._llm.structured(self._prompt(a, b), PriorLinkVerdict)
        except Exception:
            return None  # graceful (BR-A14)
        if not verdict.related or verdict.weight < self._threshold:
            return None  # BR-A8
        cross = not (set(a.domains) & set(b.domains))
        return WikiPriorLink(
            world_id=world_id,
            source_id=a.id,
            target_id=b.id,
            relation=verdict.relation or "related",
            weight=verdict.weight,
            cross_domain=cross,
            provenance=Provenance(source=SourceKind.INFERRED_WIKI, generated_by="wiki-linker"),
        )

    @staticmethod
    def _text(p: WikiPrior) -> str:
        return f"{p.condition} {p.effect} {p.description or ''}".strip()

    @staticmethod
    def _prompt(a: WikiPrior, b: WikiPrior) -> str:
        return (
            "Two common-sense priors are given. Decide if they are meaningfully "
            "related (one reinforces/implies/contrasts/causes the other). If so, "
            "give a short relation label and a strength in [0,1].\n\n"
            f"A: {a.condition} -> {a.effect}\n"
            f"B: {b.condition} -> {b.effect}"
        )
