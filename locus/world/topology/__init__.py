"""U3 Topology — region hierarchy + weighted connection graph (FR-B)."""

from locus.world.topology.builder import TopologyBuilder, collect_connection_candidates
from locus.world.topology.hierarchy import assign_hierarchy
from locus.world.topology.weights import base_weight, compute_weight, terrain_modifier

__all__ = [
    "TopologyBuilder",
    "collect_connection_candidates",
    "assign_hierarchy",
    "base_weight",
    "compute_weight",
    "terrain_modifier",
]
