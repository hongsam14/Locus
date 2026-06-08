"""U3 Topology — region hierarchy + weighted connection graph (FR-B)."""

from .builder import TopologyBuilder, collect_connection_candidates
from .hierarchy import assign_hierarchy
from .weights import base_weight, compute_weight, terrain_modifier

__all__ = [
    "TopologyBuilder",
    "collect_connection_candidates",
    "assign_hierarchy",
    "base_weight",
    "compute_weight",
    "terrain_modifier",
]
