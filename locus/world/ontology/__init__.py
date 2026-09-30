"""U4 Ontology — knowledge graph construction, scoping, corroboration, dedup."""

from locus.world.ontology.builder import OntologyBuilder, remap_scopes, scope_knowledge
from locus.world.ontology.corroboration import CorroborationGenerator
from locus.world.ontology.dedup import Deduplicator, merge_duplicates
from locus.world.ontology.similarity import candidate_pairs, cosine

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
