"""Common-sense Wiki lookup interface with LLM fallback (FR-E lookup).

NPC-facing: scoped to a single world (BR-A9). Each world holds its own
WikiPriors (no reserved partition). Topology weighting and lore corroboration
query it through this interface; cross-world reference is a separate
designer-only path (see ``cross_world.CrossWorldWikiExplorer``).

Lookup strategy:
1. Hybrid-search WikiPriors in this world's partition.
2. If a hit clears ``score_threshold`` -> return it (provenance: wiki).
3. Otherwise -> LLM fallback inference grounded on any available context
   (provenance: inferred-wiki).

U3 (Q4=A, BR-U3-29): a fallback prior is kept in ``created_priors`` so the build can
store it; the same normalized query is answered by the first prior it made, and one
wiki makes at most ``WIKI_FALLBACK_MAX``. ``fallback=False`` (augmentation, NFR R-03) or
a wiki without an LLM answers from search only.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from locus.shared.llm.base import EmbeddingProvider, LLMProvider
from locus.shared.models import PriorType, Provenance, SourceKind, WikiPrior
from locus.shared.storage.base import SearchRepository

WIKI_FALLBACK_MAX = 40  # LLM-made priors per wiki (= per build), BR-U3-29


def _query_key(query: str) -> str:
    return " ".join(query.casefold().split())


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
        llm: LLMProvider | None,
        embedding: EmbeddingProvider | None = None,
        *,
        world_id: str,
        score_threshold: float = 0.0,
    ) -> None:
        self._search = search
        self._llm = llm
        self._embedding = embedding
        self._world_id = world_id
        self._threshold = score_threshold
        self._created: dict[str, WikiPrior] = {}  # normalized query -> fallback prior
        self.fallback_capped = False  # a fallback was refused at WIKI_FALLBACK_MAX

    @property
    def created_priors(self) -> list[WikiPrior]:
        """Priors this wiki made by LLM fallback, oldest first (the build stores them)."""
        return list(self._created.values())

    # -- public API ------------------------------------------------------- #
    def lookup_terrain_rule(self, feature: str) -> list[WikiPrior]:
        """Find priors about a terrain feature (e.g. 'mountain range between regions')."""
        return self._lookup(
            query=f"terrain feature: {feature}",
            fallback_prior_type=PriorType.TERRAIN_RULE,
            k=3,
        )

    def lookup_similar(self, query: str, k: int = 5, *, fallback: bool = True) -> list[WikiPrior]:
        """Find priors semantically similar to ``query`` (e.g. 'basin climate').
        ``fallback=False`` never calls the LLM (an empty list on a search miss)."""
        return self._lookup(query=query, fallback_prior_type=PriorType.FACT, k=k, fallback=fallback)

    # -- internals -------------------------------------------------------- #
    def _lookup(
        self, query: str, fallback_prior_type: PriorType, k: int, *, fallback: bool = True
    ) -> list[WikiPrior]:
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

        if not fallback or self._llm is None:
            return []
        # graceful fallback: infer a prior from LLM world knowledge, once per query
        key = _query_key(query)
        made = self._created.get(key)
        if made is not None:
            return [made]
        if len(self._created) >= WIKI_FALLBACK_MAX:
            self.fallback_capped = True
            return []
        prior = self._fallback(query, fallback_prior_type)
        self._created[key] = prior
        return [prior]

    def _hit_to_prior(self, hit) -> WikiPrior:
        meta = hit.meta or {}
        return WikiPrior(
            id=hit.id,
            world_id=hit.world_id or self._world_id,
            prior_type=meta.get("prior_type", PriorType.FACT),
            condition=meta.get("condition", hit.text),
            effect=meta.get("effect", ""),
            domains=meta.get("domains", []),
            description=meta.get("description"),
            confidence=meta.get("confidence", 1.0),
            provenance=Provenance(source=SourceKind.INPUT, generated_by="wiki", note="wiki hit"),
        )

    def _fallback(self, query: str, prior_type: PriorType) -> WikiPrior:
        assert self._llm is not None
        prompt = (
            "You encode real-world geographic/geological/logistical common sense as a rule. "
            f"For the following query, state the condition and its real-world effect.\n\nQuery: {query}"
        )
        suggestion = self._llm.structured(prompt, _PriorSuggestion)
        return WikiPrior(
            world_id=self._world_id,
            prior_type=prior_type,
            condition=suggestion.condition,
            effect=suggestion.effect,
            description=suggestion.description or None,
            confidence=suggestion.confidence,
            provenance=Provenance(
                source=SourceKind.INFERRED,
                generated_by="llm",
                note="wiki miss -> LLM fallback",
            ),
        )
