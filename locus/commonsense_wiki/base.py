"""Common-sense Wiki lookup interface with LLM fallback (FR-E lookup, CL1=A).

The Wiki is a real-world prior knowledge base stored in the ``__realworld__``
partition (a "digital twin", CL2). Topology weighting (FR-B3) and lore
corroboration (FR-C3) query it through this interface.

Lookup strategy (business-logic-model.md §4):
1. Hybrid-search WikiPriors in the ``__realworld__`` partition.
2. If a hit clears ``score_threshold`` -> return it (provenance: wiki).
3. Otherwise -> LLM fallback inference grounded on any available context
   (provenance: inferred-wiki).

The Wiki *build* (ingesting real-world maps/text) is implemented in U6; here we
only provide lookup + graceful fallback so U3/U4 can run before U6 exists.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .. import REALWORLD_WORLD_ID
from ..llm.base import EmbeddingProvider, LLMProvider
from ..models import PriorType, Provenance, SourceKind, WikiPrior
from ..storage.base import SearchRepository


class _PriorSuggestion(BaseModel):
    """Structured LLM fallback output for a missing prior."""

    condition: str
    effect: str
    description: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class CommonsenseWiki:
    def __init__(
        self,
        search: SearchRepository,
        llm: LLMProvider,
        embedding: EmbeddingProvider | None = None,
        *,
        world_id: str = REALWORLD_WORLD_ID,
        score_threshold: float = 0.0,
    ) -> None:
        self._search = search
        self._llm = llm
        self._embedding = embedding
        self._world_id = world_id
        self._threshold = score_threshold

    # -- public API ------------------------------------------------------- #
    def lookup_terrain_rule(self, feature: str) -> list[WikiPrior]:
        """Find priors about a terrain feature (e.g. 'mountain range between regions')."""
        return self._lookup(
            query=f"terrain feature: {feature}",
            fallback_prior_type=PriorType.TERRAIN_RULE,
            k=3,
        )

    def lookup_similar(self, query: str, k: int = 5) -> list[WikiPrior]:
        """Find priors semantically similar to ``query`` (e.g. 'basin climate')."""
        return self._lookup(query=query, fallback_prior_type=PriorType.FACT, k=k)

    # -- internals -------------------------------------------------------- #
    def _lookup(self, query: str, fallback_prior_type: PriorType, k: int) -> list[WikiPrior]:
        embedding = None
        if self._embedding is not None:
            embedding = self._embedding.embed([query])[0]

        hits = self._search.hybrid_search(
            world_id=self._world_id,
            query_text=query,
            query_embedding=embedding,
            k=k,
            filters={"label": "WikiPrior"},
        )
        usable = [h for h in hits if h.score >= self._threshold]
        if usable:
            return [self._hit_to_prior(h) for h in usable]

        # graceful fallback: infer a prior from LLM world knowledge
        return [self._fallback(query, fallback_prior_type)]

    def _hit_to_prior(self, hit) -> WikiPrior:
        meta = hit.meta or {}
        return WikiPrior(
            id=hit.id,
            prior_type=meta.get("prior_type", PriorType.FACT),
            condition=meta.get("condition", hit.text),
            effect=meta.get("effect", ""),
            description=meta.get("description"),
            confidence=meta.get("confidence", 1.0),
            provenance=Provenance(source=SourceKind.INPUT, generated_by="wiki", note="wiki hit"),
        )

    def _fallback(self, query: str, prior_type: PriorType) -> WikiPrior:
        prompt = (
            "You encode real-world geographic/geological/logistical common sense as a rule. "
            f"For the following query, state the condition and its real-world effect.\n\nQuery: {query}"
        )
        suggestion = self._llm.structured(prompt, _PriorSuggestion)
        return WikiPrior(
            prior_type=prior_type,
            condition=suggestion.condition,
            effect=suggestion.effect,
            description=suggestion.description or None,
            confidence=suggestion.confidence,
            provenance=Provenance(
                source=SourceKind.INFERRED_WIKI,
                generated_by="llm",
                note="wiki miss -> LLM fallback",
            ),
        )
