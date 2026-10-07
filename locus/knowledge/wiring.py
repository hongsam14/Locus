"""knowledge boundary composition (AD-R2): ``assemble_knowledge(shared) -> KnowledgeContainer``."""

from __future__ import annotations

from dataclasses import dataclass

from locus.knowledge.cache import SnapshotSource, WorldCache
from locus.knowledge.consensus import ConsensusParams
from locus.knowledge.loader import WorldLoader
from locus.knowledge.query import QueryEngine
from locus.shared.wiring import SharedContainer


@dataclass
class KnowledgeContainer:
    loader: WorldLoader | None
    cache: SnapshotSource | None  # WorldCache in production; world/play read through it
    query: QueryEngine
    params: ConsensusParams


def assemble_knowledge(shared: SharedContainer) -> KnowledgeContainer:
    if shared.graph is None:
        raise RuntimeError("knowledge boundary needs a connected graph repository")
    params = ConsensusParams.from_tuning(shared.settings.knowledge_tuning())
    loader = WorldLoader(shared.graph)
    cache = WorldCache(loader)
    return KnowledgeContainer(
        loader=loader, cache=cache, query=QueryEngine(cache, params), params=params
    )
