"""OntologyBuilder — IngestionResult + RegionTopology -> KnowledgeGraph (U4, FR-C)."""

from __future__ import annotations

from dataclasses import dataclass, field

from locus.shared.llm.base import EmbeddingProvider, LLMProvider
from locus.shared.models import (
    BuildWarning,
    IngestionResult,
    Knowledge,
    KnowledgeGraph,
    Region,
    RegionTopology,
    ScopeLink,
    ScopeType,
)
from locus.world.ontology.corroboration import CorroborationGenerator
from locus.world.ontology.dedup import DEFAULT_SIM_THRESHOLD, Deduplicator
from locus.world.ontology.reconciler import EntityReconciler
from locus.world.topology.naming import index_by_name, resolve_region
from locus.world.wiki.base import CommonsenseWiki


@dataclass
class OntologyBuild:
    """What the ontology stage hands the builder: the graph (with
    ``unscoped_knowledge_ids`` already on canonical ids) plus its warnings (RE A4/A13)."""

    kg: KnowledgeGraph
    warnings: list[BuildWarning] = field(default_factory=list)


def scope_knowledge(
    knowledge: list[Knowledge], regions: list[Region]
) -> tuple[list[ScopeLink], list[str], list[BuildWarning]]:
    """Direct-scope each knowledge item to its region.

    Returns (scope_links, unscoped_ids, warnings). Global knowledge gets no link
    (included everywhere at query time); a ``region_hint`` that resolves (BR-U2-8,
    role=hint: most specific same-name level) -> direct link; otherwise the id is
    reported as unscoped (stored, shown in the editor — BR-U2-14). Pure.
    """
    by_name = index_by_name(regions)
    scopes: list[ScopeLink] = []
    unscoped: list[str] = []
    warnings: list[BuildWarning] = []
    for k in knowledge:
        if k.is_global:
            continue
        region = None
        if k.region_hint:
            region, warning = resolve_region(k.region_hint, by_name, role="hint", stage="ontology")
            if warning is not None:
                warning.item_id = warning.item_id or k.id
                warnings.append(warning)
        if region is None:
            unscoped.append(k.id)
            continue
        scopes.append(
            ScopeLink(
                world_id=k.world_id,
                knowledge_id=k.id,
                region_id=region.id,
                scope_type=ScopeType.DIRECT,
                confidence=k.confidence,
            )
        )
    return scopes, unscoped, warnings


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
        dedup_threshold: float = DEFAULT_SIM_THRESHOLD,
    ) -> None:
        self._llm = llm
        self._embedding = embedding
        self._wiki = wiki
        self._max_corr = max_corroborations_per_region
        self._dedup_threshold = dedup_threshold  # U7, FR-A7 (ONTOLOGY_DEDUP_THRESHOLD)

    def set_wiki(self, wiki: CommonsenseWiki | None) -> None:
        """Inject the world-scoped wiki at build time (single-world, BR-A9)."""
        self._wiki = wiki

    def build(
        self, ingestion: IngestionResult, topology: RegionTopology, *, world_id: str
    ) -> OntologyBuild:
        regions = topology.regions
        knowledge = list(ingestion.knowledge)

        # 1. corroboration (US-3.3, LLM) — appended to knowledge, scoped direct
        corr_scopes: list[ScopeLink] = []
        if self._llm is not None:
            gen = CorroborationGenerator(self._llm, self._wiki, max_per_region=self._max_corr)
            corr_knowledge, corr_scopes = gen.generate(regions, world_id=world_id)
            knowledge.extend(corr_knowledge)

        # 2. region scoping for input knowledge (US-3.2 / CL1 global)
        input_scopes, unscoped, warnings = scope_knowledge(ingestion.knowledge, regions)
        scopes = input_scopes + corr_scopes

        # 3. semantic dedup (CL2=C) over the full knowledge set
        deduper = Deduplicator(self._embedding, self._llm, threshold=self._dedup_threshold)
        deduped, remap = deduper.dedupe(knowledge)
        scopes = remap_scopes(scopes, remap)
        kept = {k.id for k in deduped}
        unscoped = list(dict.fromkeys(remap.get(i, i) for i in unscoped if remap.get(i, i) in kept))

        # 4. entity reconciliation (FR-IM4): cross-source merge + orphan connect
        about_ids = {eid for k in deduped for eid in k.about_entity_ids}
        reconciler = EntityReconciler(self._embedding, self._llm)
        rec = reconciler.reconcile(
            list(ingestion.entities), regions, list(ingestion.relations), about_ids
        )
        if rec.remap:
            for k in deduped:
                k.about_entity_ids = sorted({rec.remap.get(i, i) for i in k.about_entity_ids})

        scoped_now = {s.knowledge_id for s in scopes}
        unscoped = [
            i for i in unscoped if i not in scoped_now
        ]  # a duplicate may have carried a scope
        return OntologyBuild(
            kg=KnowledgeGraph(
                world_id=world_id,
                entities=rec.entities,
                relations=rec.relations,
                knowledge=deduped,
                scopes=scopes,
                unconnected_entity_ids=rec.unconnected_entity_ids,
                unscoped_knowledge_ids=unscoped,
            ),
            warnings=warnings,
        )
