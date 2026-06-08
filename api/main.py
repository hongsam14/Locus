"""FastAPI application factory for Locus (U8 serving + U9 authoring)."""

from __future__ import annotations

from fastapi import FastAPI

from locus.commonsense_wiki import PriorDistiller, WikiAdmin, WikiBuilder
from locus.config import get_settings
from locus.ingestion.service import IngestionService
from locus.llm.factory import ProviderFactory
from locus.ontology.builder import OntologyBuilder
from locus.query import QueryEngine, WorldLoader
from locus.services import Exporter, GraphEditor, PipelineOrchestrator
from locus.storage import Neo4jGraphRepository, OpenSearchRepository, SchemaInitializer
from locus.topology.builder import TopologyBuilder

from .routers import authoring as authoring_router
from .routers import query as query_router

_STATE_KEYS = (
    "query_engine",
    "orchestrator",
    "wiki_builder",
    "wiki_admin",
    "graph_editor",
    "exporter",
    "graph_repo",
    "augmentation_service",
)


def _wire_default(app: FastAPI) -> None:  # pragma: no cover - requires live services
    s = get_settings()
    graph = Neo4jGraphRepository(
        uri=s.neo4j_uri, user=s.neo4j_user, password=s.neo4j_password.get_secret_value()
    )
    search = OpenSearchRepository(
        url=s.opensearch_url, index=s.opensearch_index, vector_dimension=s.embedding_dimension
    )
    graph.connect()
    search.connect()
    SchemaInitializer(graph, search).initialize()

    factory = ProviderFactory(s)
    llm, embedding = factory.llm(), factory.embedding()
    from locus.commonsense_wiki.base import CommonsenseWiki

    wiki = CommonsenseWiki(search, llm, embedding)
    loader = WorldLoader(graph)

    app.state.graph_repo = graph
    app.state.query_engine = QueryEngine(loader)
    app.state.orchestrator = PipelineOrchestrator(
        IngestionService.from_factory(factory),
        TopologyBuilder(wiki=wiki),
        OntologyBuilder(llm=llm, embedding=embedding, wiki=wiki),
        graph,
        search,
        embedding,
    )
    app.state.wiki_builder = WikiBuilder(
        IngestionService.from_factory(factory),
        TopologyBuilder(wiki=None),
        OntologyBuilder(llm=llm, embedding=embedding, wiki=None),
        PriorDistiller(llm),
        graph,
        search,
        embedding,
    )
    app.state.wiki_admin = WikiAdmin(graph, search, embedding)
    editor = GraphEditor(graph, search, embedding)
    app.state.graph_editor = editor
    app.state.exporter = Exporter(loader)

    from locus.augmentation import AugmentationEngine, AugmentationService

    app.state.augmentation_service = AugmentationService(
        AugmentationEngine(loader, editor, graph, wiki=wiki, llm=llm)
    )


def create_app(**state) -> FastAPI:
    """Build the app. Pass explicit services (query_engine=..., orchestrator=...) for tests;
    if none are provided, services are wired from settings on startup."""
    app = FastAPI(title="Locus", version="0.1.0")
    for key in _STATE_KEYS:
        setattr(app.state, key, state.get(key))

    if not any(state.get(k) for k in _STATE_KEYS):

        @app.on_event("startup")
        def _startup() -> None:  # pragma: no cover - requires live DB
            _wire_default(app)

    @app.get("/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(query_router.router)
    app.include_router(authoring_router.router)
    return app


# Module-level app for `uvicorn api.main:app`.
app = create_app()
