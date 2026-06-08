"""Deterministic similarity measures for ontology dedup (U4).

Home for *measurement* of how alike two items are — independent of any
merge *policy* (that lives in ``dedup.py``). Currently vector cosine; designed
to grow toward structural / terrain-relationship similarity later.

Pure / no external dependencies → trivially unit-testable & PBT-friendly.
"""

from __future__ import annotations

import math


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity in [-1, 1]; 0.0 for degenerate (zero/empty) vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def candidate_pairs(vectors: list[list[float]], threshold: float) -> list[tuple[int, int]]:
    """Index pairs (i<j) whose cosine similarity is >= ``threshold``."""
    pairs: list[tuple[int, int]] = []
    n = len(vectors)
    for i in range(n):
        for j in range(i + 1, n):
            if cosine(vectors[i], vectors[j]) >= threshold:
                pairs.append((i, j))
    return pairs
