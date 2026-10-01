"""Length caps on LLM output before it is stored (U6 NFR N6-2).

What an LLM writes about a deed travels on: into the deed row, a seed rumor, a spread
prompt and other NPCs' prompts. Cutting it here bounds every later prompt and blunts an
injection that tries to smuggle a long instruction through a summary (NFR-6, N6-5).
"""

from __future__ import annotations

NARRATION_MAX = 1000  # the player-facing narration (display language)
LINE_MAX = 300  # a deed record, a talk summary, a retelling (English)
SLANT_MAX = 40  # one or two words


def cap(text: str | None, limit: int) -> str:
    """``text`` stripped and cut to ``limit`` characters (empty for None)."""
    return (text or "").strip()[:limit].strip()
