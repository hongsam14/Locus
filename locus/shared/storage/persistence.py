"""Shared world persistence (U9; reused by U6 wiki build).

Assembles domain models into storage nodes/edges + search docs and writes them
through the repository ports. Graceful: failures append to ``warnings`` rather
than aborting.
"""

from __future__ import annotations

from datetime import UTC, datetime

from locus.shared.llm.base import EmbeddingProvider
from locus.shared.models import (
    NPC,
    BuildWarning,
    ConnectionEdge,
    Entity,
    Knowledge,
    Region,
    Relation,
    ScopeLink,
    WikiPrior,
    WikiPriorLink,
    WorldMeta,
)
from locus.shared.storage import graph_mapping as gm
from locus.shared.storage.base import ConstraintViolation, GraphRepository, SearchRepository


def persist_graph(
    graph_repo: GraphRepository,
    search_repo: SearchRepository,
    embedding: EmbeddingProvider | None,
    world_id: str,
    *,
    regions: list[Region] | None = None,
    entities: list[Entity] | None = None,
    knowledge: list[Knowledge] | None = None,
    priors: list[WikiPrior] | None = None,
    prior_links: list[WikiPriorLink] | None = None,
    connections: list[ConnectionEdge] | None = None,
    scopes: list[ScopeLink] | None = None,
    relations: list[Relation] | None = None,
    npcs: list[NPC] | None = None,
    meta: WorldMeta | None = None,
    warnings: list[BuildWarning] | None = None,
) -> list[BuildWarning]:
    regions = regions or []
    entities = entities or []
    knowledge = knowledge or []
    priors = priors or []
    prior_links = prior_links or []
    connections = connections or []
    scopes = scopes or []
    relations = relations or []
    npcs = npcs or []
    warnings = warnings if warnings is not None else []

    nodes = (
        [gm.region_to_node(r) for r in regions]
        + [gm.entity_to_node(e) for e in entities]
        + [gm.knowledge_to_node(k) for k in knowledge]
        + [gm.wikiprior_to_node(p) for p in priors]
        + [gm.npc_to_node(n) for n in npcs]
        + ([gm.worldmeta_to_node(meta)] if meta is not None else [])
    )
    edges = (
        gm.contains_edges(regions)
        + gm.connection_edges(connections)
        + gm.scope_edges(scopes)
        + gm.about_edges(knowledge)
        + gm.derived_from_edges(knowledge)
        + gm.relation_edges(relations)
        + gm.located_in_edges(entities)
        + gm.prior_link_edges(prior_links)
        + gm.lives_in_edges(npcs)
    )
    try:
        graph_repo.upsert_nodes(nodes)
        graph_repo.upsert_edges(edges)
    except ConstraintViolation as exc:  # ids clash with another world (BR-U2-4)
        warnings.append(
            BuildWarning(
                stage="persist-graph",
                severity="error",
                message=f"id collision with another world; retry with remap=true ({exc})",
            )
        )
        return warnings  # do not touch the search index: OpenSearch keys docs by bare id
    except Exception as exc:  # graceful, but the build/import is not ok (BR-U2-13)
        warnings.append(BuildWarning(stage="persist-graph", severity="error", message=str(exc)))
        return warnings

    docs = (
        [gm.knowledge_doc(k) for k in knowledge]
        + [gm.entity_doc(e) for e in entities]
        + [gm.wikiprior_doc(p) for p in priors]
        + [gm.npc_doc(n) for n in npcs]
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
            warnings.append(
                BuildWarning(stage="persist-search", severity="error", message=str(exc))
            )
    return warnings


def touch_world_meta(graph_repo: GraphRepository, world_id: str, *, last_writer: str) -> bool:
    """Refresh ``WorldMeta.updated_at``/``last_writer`` after an edit (BR-U2-23). Returns
    False when the world has no meta node yet (pre-U2 worlds) — nothing is created."""
    nodes = graph_repo.find_nodes(world_id, "WorldMeta")
    if not nodes:
        return False
    meta = gm.node_to_worldmeta(nodes[0]).model_copy(
        update={"updated_at": datetime.now(UTC), "last_writer": last_writer}
    )
    graph_repo.upsert_nodes([gm.worldmeta_to_node(meta)])
    return True
