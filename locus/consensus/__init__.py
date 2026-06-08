"""U5 Consensus — region knowledge consensus, propagation, distortion (FR-D)."""

from .engine import ConsensusEngine, ConsensusParams, compute_consensus
from .propagation import best_path_weights

__all__ = [
    "ConsensusEngine",
    "ConsensusParams",
    "compute_consensus",
    "best_path_weights",
]
