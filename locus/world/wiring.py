"""world boundary composition (AD-R2): ``assemble_world(shared, knowledge) -> WorldContainer``.

Graph + search + the knowledge cache are enough for the LLM-free services (editor,
World File export/import, demo load, world list, the augmentation Q&A on templates).
The builder and NPC drafts need an LLM and stay ``None`` without one, so an API key
is not required to open the editor or load the demo (NFR-4, review R-14).
"""

from __future__ import annotations

from dataclasses import dataclass

from locus.knowledge.cache import SnapshotCache
from locus.knowledge.wiring import KnowledgeContainer
from locus.shared.wiring import SharedContainer
from locus.world.augmentation import AugmentationEngine, AugmentationService
from locus.world.build import WorldBuilder
from locus.world.demo import DemoWorlds
from locus.world.editor import Editors, WorldCatalog
from locus.world.npc_drafts import NpcDraftService
from locus.world.wiki import CommonsenseWiki, CrossWorldWikiExplorer, WikiAdmin
from locus.world.worldfile.export import WorldFileExporter
from locus.world.worldfile.import_ import WorldFileImporter


@dataclass
class WorldContainer:
    cache: SnapshotCache | None
    editors: Editors | None  # U3: the editor classes (was one WorldEditor)
    exporter: WorldFileExporter | None
    importer: WorldFileImporter | None
    demo: DemoWorlds | None
    catalog: WorldCatalog | None = None  # U3: the `/` world list (was a router query)
    # LLM-dependent (None without a provider -> their routes answer 503)
    builder: WorldBuilder | None = None
    augmentation: AugmentationService | None = None
    npc_drafts: NpcDraftService | None = None  # U3 W8: one LLM call per request
    # LLM-free wiki tools (None only in tests that do not wire them)
    wiki_admin: WikiAdmin | None = None
    cross_world: CrossWorldWikiExplorer | None = None


def assemble_world(shared: SharedContainer, knowledge: KnowledgeContainer) -> WorldContainer:
    if shared.graph is None or shared.search is None:
        raise RuntimeError("world boundary needs connected graph and search repositories")
    if knowledge.cache is None or not hasattr(knowledge.cache, "invalidate"):
        raise RuntimeError("world boundary needs the knowledge WorldCache")
    graph, search, embedding = shared.graph, shared.search, shared.embedding
    cache: SnapshotCache = knowledge.cache  # type: ignore[assignment]
    backup_dir = shared.settings.backup_dir

    editors = Editors.assemble(graph, search, embedding, cache=cache)
    exporter = WorldFileExporter(cache)
    importer = WorldFileImporter(
        graph, search, embedding, cache, exporter=exporter, backup_dir=backup_dir
    )
    container = WorldContainer(
        cache=cache,
        editors=editors,
        catalog=WorldCatalog(graph),
        exporter=exporter,
        importer=importer,
        demo=None,
        wiki_admin=WikiAdmin(graph, search, embedding, cache=cache),
        cross_world=CrossWorldWikiExplorer(graph, search, embedding),
    )

    def wiki_for(world_id: str) -> CommonsenseWiki:  # single-world (BR-A9), search only
        return CommonsenseWiki(search, None, embedding, world_id=world_id)  # NFR R-03

    # The Q&A runs without an LLM on templates and skips wiki conflicts (U3 NFR-4)
    container.augmentation = AugmentationService(AugmentationEngine(editors))

    builder: WorldBuilder | None = None
    if shared.llm is not None and shared.factory is not None:
        llm = shared.llm
        builder = WorldBuilder.from_factory(
            shared.factory,
            graph,
            search,
            cache=cache,
            exporter=exporter,
            backup_dir=backup_dir,
            tuning=shared.settings.world_tuning(),  # U7, FR-A7
        )
        container.builder = builder
        container.npc_drafts = NpcDraftService(llm, cache)
        container.augmentation = AugmentationService(
            AugmentationEngine(editors, wiki_provider=wiki_for, llm=llm)
        )
    container.demo = DemoWorlds(importer, builder)
    return container
