"""knowledge — the read-only core that computes what a region's inhabitants know.

Consensus (direct / inherited / global / propagated / hearsay), the world
loader, and the query engine. Depends only on ``shared``; ``world`` and ``play``
both read through this boundary (FR-A1/A2).
"""

from locus.knowledge.cache import SnapshotSource, WorldCache
from locus.knowledge.consensus import (
    DEFAULT_PARAMS,
    ConsensusEngine,
    ConsensusParams,
    compute_consensus,
)
from locus.knowledge.loader import WorldLoader
from locus.knowledge.propagation import best_path_weights
from locus.knowledge.query import (
    QueryEngine,
    diff_sets,
    region_briefs,
    region_known,
    split_shared_unique,
    view_items,
)
from locus.knowledge.wiring import KnowledgeContainer, assemble_knowledge

__all__ = [
    "DEFAULT_PARAMS",
    "ConsensusEngine",
    "ConsensusParams",
    "compute_consensus",
    "best_path_weights",
    "WorldLoader",
    "WorldCache",
    "SnapshotSource",
    "region_briefs",
    "QueryEngine",
    "view_items",
    "region_known",
    "split_shared_unique",
    "diff_sets",
    "KnowledgeContainer",
    "assemble_knowledge",
]
