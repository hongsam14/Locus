"""Shared world persistence (U9; reused by U6 wiki build).

Assembles domain models into storage nodes/edges + search docs and writes them
through the repository ports. Graceful: failures append to ``warnings`` rather
than aborting.
"""

from __future__ import annotations

from ..llm.base import EmbeddingProvider
from ..models import (
    BuildWarning,
    ConnectionEdge,
    Entity,
    Knowledge,
    Region,
    Relation,
    Rumor,
    ScopeLink,
    WikiPrior,
)
from . import graph_mapping as gm
from .base import GraphRepository, SearchRepository


def persist_graph(
    graph_repo: GraphRepository,
    search_repo: SearchRepository,
    embedding: EmbeddingProvider | None,
    world_id: str,
    *,
    regions: list[Region] | None = None,
    entities: list[Entity] | None = None,
    knowledge: list[Knowledge] | None = None,
    rumors: list[Rumor] | None = None,
    priors: list[WikiPrior] | None = None,
    connections: list[ConnectionEdge] | None = None,
    scopes: list[ScopeLink] | None = None,
    relations: list[Relation] | None = None,
    warnings: list[BuildWarning] | None = None,
) -> list[BuildWarning]:
    regions = regions or []
    entities = entities or []
    knowledge = knowledge or []
    rumors = rumors or []
    priors = priors or []
    connections = connections or []
    scopes = scopes or []
    relations = relations or []
    warnings = warnings if warnings is not None else []

    nodes = (
        [gm.region_to_node(r) for r in regions]
        + [gm.entity_to_node(e) for e in entities]
        + [gm.knowledge_to_node(k) for k in knowledge]
        + [gm.rumor_to_node(r) for r in rumors]
        + [gm.wikiprior_to_node(p, world_id) for p in priors]
    )
    edges = (
        gm.contains_edges(regions)
        + gm.connection_edges(connections)
        + gm.scope_edges(scopes)
        + gm.about_edges(knowledge)
        + gm.derived_from_edges(knowledge)
        + gm.relation_edges(relations)
        + gm.distorted_from_edges(rumors)
    )
    try:
        graph_repo.upsert_nodes(nodes)
        graph_repo.upsert_edges(edges)
    except Exception as exc:  # graceful
        warnings.append(BuildWarning(stage="persist-graph", message=str(exc)))

    docs = (
        [gm.knowledge_doc(k) for k in knowledge]
        + [gm.entity_doc(e) for e in entities]
        + [gm.wikiprior_doc(p, world_id) for p in priors]
    )
    docs = [d for d in docs if d.text.strip()]
    if docs:
        if embedding is not None:
            try:
                vectors = embedding.embed([d.text for d in docs])
                for doc, vec in zip(docs, vectors, strict=True):
                    doc.embedding = vec
            except Exception as exc:
                warnings.append(BuildWarning(stage="embed", message=str(exc)))
        try:
            search_repo.index(docs)
        except Exception as exc:
            warnings.append(BuildWarning(stage="persist-search", message=str(exc)))
    return warnings
