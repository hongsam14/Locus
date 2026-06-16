"""PipelineOrchestrator — end-to-end world build (U9, FD9-Q1=A).

Each world now self-distills its own WikiPriors and links them, then builds
ontology against its own single-world wiki (BR-A9, BR-A12).
"""

from __future__ import annotations

from ..commonsense_wiki.base import CommonsenseWiki
from ..commonsense_wiki.distiller import PriorDistiller
from ..commonsense_wiki.linker import WikiPriorLinker
from ..ingestion.service import IngestionService, WorldInputs
from ..llm.factory import ProviderFactory
from ..models import BuildReport, SourceKind
from ..ontology.builder import OntologyBuilder
from ..storage.base import GraphRepository, SearchRepository
from ..storage.persistence import persist_graph
from ..topology.builder import TopologyBuilder


class PipelineOrchestrator:
    def __init__(
        self,
        ingestion_service: IngestionService,
        topology_builder: TopologyBuilder,
        ontology_builder: OntologyBuilder,
        graph_repo: GraphRepository,
        search_repo: SearchRepository,
        embedding=None,
        distiller: PriorDistiller | None = None,
        linker: WikiPriorLinker | None = None,
        llm=None,
    ) -> None:
        self._ingest = ingestion_service
        self._topology = topology_builder
        self._ontology = ontology_builder
        self._graph = graph_repo
        self._search = search_repo
        self._embedding = embedding
        self._distiller = distiller
        self._linker = linker
        self._llm = llm

    @classmethod
    def from_factory(
        cls,
        factory: ProviderFactory,
        graph_repo: GraphRepository,
        search_repo: SearchRepository,
    ) -> PipelineOrchestrator:
        llm = factory.llm()
        embedding = factory.embedding()
        return cls(
            ingestion_service=IngestionService.from_factory(factory),
            topology_builder=TopologyBuilder(wiki=None),
            ontology_builder=OntologyBuilder(llm=llm, embedding=embedding, wiki=None),
            graph_repo=graph_repo,
            search_repo=search_repo,
            embedding=embedding,
            distiller=PriorDistiller(llm),
            linker=WikiPriorLinker(llm, embedding),
            llm=llm,
        )

    def build_world(self, world_id: str, inputs: WorldInputs) -> BuildReport:
        warnings: list = []
        ingestion = self._ingest.ingest_all(world_id, inputs)
        topology = self._topology.build(ingestion, world_id=world_id)

        # this world's own commonsense priors + their links (BR-A12)
        priors = (
            self._distiller.distill(ingestion, topology, world_id=world_id)
            if self._distiller
            else []
        )
        prior_links = (
            self._linker.link(priors, world_id=world_id) if self._linker and priors else []
        )

        # persist priors first so corroboration's single-world wiki can find them
        if priors:
            persist_graph(
                self._graph,
                self._search,
                self._embedding,
                world_id,
                priors=priors,
                prior_links=prior_links,
                warnings=warnings,
            )

        # NPC-facing build uses ONLY this world's wiki (BR-A9)
        if self._llm is not None:
            wiki = CommonsenseWiki(self._search, self._llm, self._embedding, world_id=world_id)
            if hasattr(self._ontology, "set_wiki"):
                self._ontology.set_wiki(wiki)
            if hasattr(self._topology, "set_wiki"):
                self._topology.set_wiki(wiki)
        kg = self._ontology.build(ingestion, topology, world_id=world_id)

        persist_graph(
            self._graph,
            self._search,
            self._embedding,
            world_id,
            regions=topology.regions,
            entities=kg.entities,
            knowledge=kg.knowledge,
            connections=topology.connections,
            scopes=kg.scopes,
            relations=kg.relations,
            warnings=warnings,
        )

        corroborations = sum(
            1 for k in kg.knowledge if str(k.provenance.source) == SourceKind.INFERRED_WIKI.value
        )
        return BuildReport(
            world_id=world_id,
            regions_created=len(topology.regions),
            connections_created=len(topology.connections),
            entities_created=len(kg.entities),
            knowledge_created=len(kg.knowledge),
            corroborations_created=corroborations,
            warnings=warnings,
        )
