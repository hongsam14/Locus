"""OntologyBuilder — IngestionResult + RegionTopology -> KnowledgeGraph (U4, FR-C)."""

from __future__ import annotations

from ..commonsense_wiki.base import CommonsenseWiki
from ..llm.base import EmbeddingProvider, LLMProvider
from ..models import (
    IngestionResult,
    Knowledge,
    KnowledgeGraph,
    Region,
    RegionTopology,
    ScopeLink,
    ScopeType,
)
from .corroboration import CorroborationGenerator
from .dedup import Deduplicator
from .reconciler import EntityReconciler


def _norm(name: str) -> str:
    return " ".join(name.strip().lower().split())


def scope_knowledge(
    knowledge: list[Knowledge], regions: list[Region]
) -> tuple[list[ScopeLink], list[str]]:
    """Direct-scope each knowledge item to its region.

    Returns (scope_links, unscoped_ids). Global knowledge gets no link (included
    everywhere at query time); region_hint that resolves -> direct link; else
    the id is reported as unscoped (augmentation candidate). Pure.
    """
    by_name = {_norm(r.name): r.id for r in regions}
    scopes: list[ScopeLink] = []
    unscoped: list[str] = []
    for k in knowledge:
        if k.is_global:
            continue
        region_id = by_name.get(_norm(k.region_hint)) if k.region_hint else None
        if region_id is None:
            unscoped.append(k.id)
            continue
        scopes.append(
            ScopeLink(
                world_id=k.world_id,
                knowledge_id=k.id,
                region_id=region_id,
                scope_type=ScopeType.DIRECT,
                confidence=k.confidence,
            )
        )
    return scopes, unscoped


def remap_scopes(scopes: list[ScopeLink], remap: dict[str, str]) -> list[ScopeLink]:
    """Repoint scope links onto canonical knowledge ids after dedup; drop dups."""
    seen: set[tuple[str, str]] = set()
    out: list[ScopeLink] = []
    for s in scopes:
        kid = remap.get(s.knowledge_id, s.knowledge_id)
        key = (kid, s.region_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(s.model_copy(update={"knowledge_id": kid}))
    return out


class OntologyBuilder:
    def __init__(
        self,
        llm: LLMProvider | None = None,
        embedding: EmbeddingProvider | None = None,
        wiki: CommonsenseWiki | None = None,
        *,
        max_corroborations_per_region: int = 2,
    ) -> None:
        self._llm = llm
        self._embedding = embedding
        self._wiki = wiki
        self._max_corr = max_corroborations_per_region

    def set_wiki(self, wiki: CommonsenseWiki | None) -> None:
        """Inject the world-scoped wiki at build time (single-world, BR-A9)."""
        self._wiki = wiki

    def build(
        self, ingestion: IngestionResult, topology: RegionTopology, *, world_id: str
    ) -> KnowledgeGraph:
        regions = topology.regions
        knowledge = list(ingestion.knowledge)

        # 1. corroboration (US-3.3, LLM) — appended to knowledge, scoped direct
        corr_scopes: list[ScopeLink] = []
        if self._llm is not None:
            gen = CorroborationGenerator(self._llm, self._wiki, max_per_region=self._max_corr)
            corr_knowledge, corr_scopes = gen.generate(regions, world_id=world_id)
            knowledge.extend(corr_knowledge)

        # 2. region scoping for input knowledge (US-3.2 / CL1 global)
        input_scopes, _unscoped = scope_knowledge(ingestion.knowledge, regions)
        scopes = input_scopes + corr_scopes

        # 3. semantic dedup (CL2=C) over the full knowledge set
        deduper = Deduplicator(self._embedding, self._llm)
        deduped, remap = deduper.dedupe(knowledge)
        scopes = remap_scopes(scopes, remap)

        # 4. entity reconciliation (FR-IM4): cross-source merge + orphan connect
        about_ids = {eid for k in deduped for eid in k.about_entity_ids}
        reconciler = EntityReconciler(self._embedding, self._llm)
        rec = reconciler.reconcile(
            list(ingestion.entities), regions, list(ingestion.relations), about_ids
        )
        if rec.remap:
            for k in deduped:
                k.about_entity_ids = sorted({rec.remap.get(i, i) for i in k.about_entity_ids})

        return KnowledgeGraph(
            world_id=world_id,
            entities=rec.entities,
            relations=rec.relations,
            knowledge=deduped,
            scopes=scopes,
            unconnected_entity_ids=rec.unconnected_entity_ids,
        )
