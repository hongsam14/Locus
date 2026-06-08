"""Knowledge deduplication policy (U4, CL2=C).

Two-stage *policy* on top of similarity *measurement*:
  1. similarity.candidate_pairs proposes near-duplicate pairs (cheap, deterministic);
  2. the LLM judges each candidate pair (merging is sensitive, so a high cosine
     alone never auto-merges).
Falls back to exact normalized-statement merge if embedding/LLM is unavailable.
"""

from __future__ import annotations

import re

from ..llm.base import EmbeddingProvider, LLMProvider
from ..models import Knowledge
from .schemas import DuplicateVerdict
from .similarity import candidate_pairs

DEFAULT_SIM_THRESHOLD = 0.86
_WS_RE = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _WS_RE.sub(" ", text.strip().lower())


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)

    def clusters(self) -> list[list[int]]:
        groups: dict[int, list[int]] = {}
        for i in range(len(self.parent)):
            groups.setdefault(self.find(i), []).append(i)
        return list(groups.values())


def merge_duplicates(
    knowledge: list[Knowledge], clusters: list[list[int]]
) -> tuple[list[Knowledge], dict[str, str]]:
    """Merge each cluster into a canonical item. Returns (merged, remap old_id->canonical_id).

    Pure: canonical = highest confidence; union of about/derived; confidence=max;
    is_global = any.
    """
    merged: list[Knowledge] = []
    remap: dict[str, str] = {}
    for cluster in clusters:
        items = [knowledge[i] for i in cluster]
        canonical = max(items, key=lambda k: k.confidence)
        about = set(canonical.about_entity_ids)
        derived = set(canonical.derived_from_prior_ids)
        is_global = False
        for it in items:
            about.update(it.about_entity_ids)
            derived.update(it.derived_from_prior_ids)
            is_global = is_global or it.is_global
            remap[it.id] = canonical.id
        canonical.about_entity_ids = sorted(about)
        canonical.derived_from_prior_ids = sorted(derived)
        canonical.is_global = is_global
        merged.append(canonical)
    return merged, remap


def _exact_clusters(knowledge: list[Knowledge]) -> list[list[int]]:
    by_norm: dict[str, list[int]] = {}
    for i, k in enumerate(knowledge):
        by_norm.setdefault(_norm(k.statement), []).append(i)
    return list(by_norm.values())


class Deduplicator:
    def __init__(
        self,
        embedding: EmbeddingProvider | None,
        llm: LLMProvider | None,
        *,
        threshold: float = DEFAULT_SIM_THRESHOLD,
    ) -> None:
        self._embedding = embedding
        self._llm = llm
        self._threshold = threshold

    def dedupe(self, knowledge: list[Knowledge]) -> tuple[list[Knowledge], dict[str, str]]:
        if len(knowledge) < 2:
            return list(knowledge), {k.id: k.id for k in knowledge}

        # Stage 0: try semantic; fall back to exact on any failure.
        if self._embedding is None or self._llm is None:
            return merge_duplicates(knowledge, _exact_clusters(knowledge))
        try:
            vectors = self._embedding.embed([k.statement for k in knowledge])
        except Exception:
            return merge_duplicates(knowledge, _exact_clusters(knowledge))

        # Stage 1: similarity proposes candidates.
        pairs = candidate_pairs(vectors, self._threshold)

        # Stage 2: LLM confirms each candidate (sensitive merge).
        uf = _UnionFind(len(knowledge))
        for i, j in pairs:
            try:
                verdict = self._llm.structured(
                    self._verdict_prompt(knowledge[i].statement, knowledge[j].statement),
                    DuplicateVerdict,
                )
            except Exception:
                continue
            if verdict.is_duplicate:
                uf.union(i, j)

        return merge_duplicates(knowledge, uf.clusters())

    @staticmethod
    def _verdict_prompt(a: str, b: str) -> str:
        return (
            "Do these two world-knowledge statements assert the SAME fact "
            "(just worded differently)? Answer is_duplicate accordingly.\n\n"
            f"A: {a}\nB: {b}"
        )
