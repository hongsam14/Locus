"""PipelineOrchestrator — end-to-end world build (U9, FD9-Q1=A)."""

from __future__ import annotations

from ..commonsense_wiki.base import CommonsenseWiki
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
    ) -> None:
        self._ingest = ingestion_service
        self._topology = topology_builder
        self._ontology = ontology_builder
        self._graph = graph_repo
        self._search = search_repo
        self._embedding = embedding

    @classmethod
    def from_factory(
        cls,
        factory: ProviderFactory,
        graph_repo: GraphRepository,
        search_repo: SearchRepository,
    ) -> PipelineOrchestrator:
        llm = factory.llm()
        embedding = factory.embedding()
        wiki = CommonsenseWiki(search_repo, llm, embedding)
        return cls(
            ingestion_service=IngestionService.from_factory(factory),
            topology_builder=TopologyBuilder(wiki=wiki),
            ontology_builder=OntologyBuilder(llm=llm, embedding=embedding, wiki=wiki),
            graph_repo=graph_repo,
            search_repo=search_repo,
            embedding=embedding,
        )

    def build_world(self, world_id: str, inputs: WorldInputs) -> BuildReport:
        warnings: list = []
        ingestion = self._ingest.ingest_all(world_id, inputs)
        topology = self._topology.build(ingestion, world_id=world_id)
        kg = self._ontology.build(ingestion, topology, world_id=world_id)

        persist_graph(
            self._graph,
            self._search,
            self._embedding,
            world_id,
            regions=topology.regions,
            entities=kg.entities,
            knowledge=kg.knowledge,
            rumors=kg.rumors,
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
            rumors_created=len(kg.rumors),
            corroborations_created=corroborations,
            warnings=warnings,
        )
