"""WikiBuilder — build the real-world Common-sense Wiki (U6, FR-E/A6).

Reuses the SAME ingestion -> topology -> ontology pipeline on real-world inputs
(digital twin, Q1=B), distills WikiPriors (Q3=A), and persists everything to the
``__realworld__`` partition (append, Q5=B). The U1 lookup then finds it.
"""

from __future__ import annotations

from .. import REALWORLD_WORLD_ID
from ..ingestion.service import IngestionService, WorldInputs
from ..llm.base import EmbeddingProvider
from ..models import BuildWarning, WikiBuildReport
from ..ontology.builder import OntologyBuilder
from ..storage.base import GraphRepository, SearchRepository
from ..storage.persistence import persist_graph
from ..topology.builder import TopologyBuilder
from .distiller import PriorDistiller


class WikiBuilder:
    def __init__(
        self,
        ingestion_service: IngestionService,
        topology_builder: TopologyBuilder,
        ontology_builder: OntologyBuilder,
        distiller: PriorDistiller | None,
        graph_repo: GraphRepository,
        search_repo: SearchRepository,
        embedding: EmbeddingProvider | None = None,
    ) -> None:
        self._ingest = ingestion_service
        self._topology = topology_builder
        self._ontology = ontology_builder
        self._distiller = distiller
        self._graph = graph_repo
        self._search = search_repo
        self._embedding = embedding

    def build_wiki(self, inputs: WorldInputs) -> WikiBuildReport:
        wid = REALWORLD_WORLD_ID
        warnings: list[BuildWarning] = []

        ingestion = self._ingest.ingest_all(wid, inputs)
        topology = self._topology.build(ingestion, world_id=wid)
        kg = self._ontology.build(ingestion, topology, world_id=wid)
        priors = (
            self._distiller.distill(ingestion, topology, world_id=wid) if self._distiller else []
        )

        persist_graph(
            self._graph,
            self._search,
            self._embedding,
            wid,
            regions=topology.regions,
            entities=kg.entities,
            knowledge=kg.knowledge,
            priors=priors,
            connections=topology.connections,
            scopes=kg.scopes,
            relations=kg.relations,
            warnings=warnings,
        )

        return WikiBuildReport(
            world_id=wid,
            regions=len(topology.regions),
            entities=len(kg.entities),
            knowledge=len(kg.knowledge),
            priors=len(priors),
            warnings=warnings,
        )
