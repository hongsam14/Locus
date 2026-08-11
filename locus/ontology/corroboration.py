"""Wiki-grounded corroboration generation (U4, US-3.3 / SC-4, Q3=B).

For each region, the LLM proposes a few corroborating facts grounded on the
region's terrain/context and (when available) Common-sense Wiki priors. Output
becomes region-scoped Knowledge with ``source=inferred-wiki`` and a confidence
discounted by 0.8 (Q5=A) to reflect that it is inferred.
"""

from __future__ import annotations

from ..commonsense_wiki.base import CommonsenseWiki
from ..llm.base import LLMProvider
from ..models import (
    Knowledge,
    Provenance,
    Region,
    ScopeLink,
    ScopeType,
    SourceKind,
    fallback_title,
)
from .schemas import CorroborationBatch

CONFIDENCE_DISCOUNT = 0.8


class CorroborationGenerator:
    def __init__(
        self,
        llm: LLMProvider,
        wiki: CommonsenseWiki | None = None,
        *,
        max_per_region: int = 2,
    ) -> None:
        self._llm = llm
        self._wiki = wiki
        self._max = max_per_region

    def generate(
        self, regions: list[Region], *, world_id: str
    ) -> tuple[list[Knowledge], list[ScopeLink]]:
        knowledge: list[Knowledge] = []
        scopes: list[ScopeLink] = []
        for region in regions:
            ctx, prior_ids = self._context(region)
            try:
                batch = self._llm.structured(self._prompt(region, ctx), CorroborationBatch)
            except Exception:
                continue  # graceful degrade (BR-U4-8)
            for sug in batch.items[: self._max]:
                k = Knowledge(
                    world_id=world_id,
                    statement=sug.statement,
                    title=sug.title or fallback_title(sug.statement),
                    topic=sug.topic,
                    confidence=min(1.0, sug.confidence * CONFIDENCE_DISCOUNT),
                    derived_from_prior_ids=prior_ids,
                    provenance=Provenance(
                        source=SourceKind.INFERRED_WIKI,
                        generated_by="llm",
                        refs=prior_ids,
                        note=sug.rationale or None,
                    ),
                )
                knowledge.append(k)
                scopes.append(
                    ScopeLink(
                        world_id=world_id,
                        knowledge_id=k.id,
                        region_id=region.id,
                        scope_type=ScopeType.DIRECT,
                        confidence=k.confidence,
                    )
                )
        return knowledge, scopes

    def _context(self, region: Region) -> tuple[str, list[str]]:
        bits = [f"name={region.name}", f"level={region.level}"]
        if region.description:
            bits.append(f"desc={region.description}")
        for key, val in region.attributes.items():
            if key not in {"parent_name", "connection_hints"}:
                bits.append(f"{key}={val}")
        ctx = "; ".join(str(b) for b in bits)

        prior_ids: list[str] = []
        if self._wiki is not None:
            try:
                priors = self._wiki.lookup_similar(ctx, k=3)
                prior_ids = [p.id for p in priors]
                if priors:
                    ctx += " | real-world priors: " + "; ".join(p.effect for p in priors)
            except Exception:
                pass
        return ctx, prior_ids

    def _prompt(self, region: Region, ctx: str) -> str:
        return (
            "Given this game-world region and real-world common-sense priors, propose up to "
            f"{self._max} plausible corroborating facts a local would take for granted "
            "(climate, logistics, customs implied by the terrain). Keep them specific.\n\n"
            f"Region: {ctx}"
        )
