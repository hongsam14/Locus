"""LlmBudget — per-turn cap on LLM calls (U4; BR-U4-17/21, NFR-5).

One rumor-chain degree step is one LLM call, so callers reserve calls with
``take(n)`` for the ``n`` degree steps they hand the generator. ``used`` is the
number of *reserved* calls: an upper bound when a chain stops early (FD R-13).
"""

from __future__ import annotations


class LlmBudget:
    def __init__(self, max_calls: int) -> None:
        self._max = max(0, int(max_calls))
        self._used = 0

    @property
    def max_calls(self) -> int:
        return self._max

    @property
    def used(self) -> int:
        return self._used

    @property
    def remaining(self) -> int:
        return self._max - self._used

    @property
    def exhausted(self) -> bool:
        return self.remaining <= 0

    def take(self, n: int) -> None:
        """Reserve ``n`` calls (never beyond the cap)."""
        if n < 0:
            raise ValueError("n must be >= 0")
        self._used = min(self._max, self._used + n)
