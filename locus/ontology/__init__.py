"""U4 Ontology — knowledge graph construction, scoping, corroboration, dedup."""

from .builder import OntologyBuilder, remap_scopes, scope_knowledge
from .corroboration import CorroborationGenerator
from .dedup import Deduplicator, merge_duplicates
from .similarity import candidate_pairs, cosine

__all__ = [
    "OntologyBuilder",
    "scope_knowledge",
    "remap_scopes",
    "CorroborationGenerator",
    "Deduplicator",
    "merge_duplicates",
    "cosine",
    "candidate_pairs",
]
