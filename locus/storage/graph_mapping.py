"""Pure mapping: domain models -> storage Node/Edge/SearchDoc (shared).

Introduced in U6 (wiki persistence); reused by U9 (world persistence). Keeps
adapters dumb and persistence logic unit-testable. Neo4j stores only primitive
properties, so nested structures (provenance, attributes) are flattened /
JSON-encoded here.
"""

from __future__ import annotations

import json

from ..models import (
    ConnectionEdge,
    Entity,
    Knowledge,
    Provenance,
    Region,
    Relation,
    ScopeLink,
    SearchDoc,
    WikiPrior,
    WikiPriorLink,
    fallback_title,
)
from .base import Edge, Node


def _flatten(props: dict) -> dict:
    """Flatten a model dump into Neo4j-safe primitive properties."""
    out: dict = {}
    for key, val in props.items():
        if key == "provenance" and isinstance(val, dict):
            out["prov_source"] = val.get("source")
            out["prov_generated_by"] = val.get("generated_by")
            if val.get("note"):
                out["prov_note"] = val["note"]
            continue
        if isinstance(val, dict):
            out[key] = json.dumps(val, ensure_ascii=False)
        elif isinstance(val, list) and not all(isinstance(x, str) for x in val):
            out[key] = json.dumps(val, ensure_ascii=False)
        else:
            out[key] = val
    return {k: v for k, v in out.items() if v is not None}


# --------------------------------------------------------------------------- #
# Nodes
# --------------------------------------------------------------------------- #
def region_to_node(r: Region) -> Node:
    return Node(id=r.id, label="Region", world_id=r.world_id, properties=_flatten(r.model_dump()))


def entity_to_node(e: Entity) -> Node:
    return Node(id=e.id, label="Entity", world_id=e.world_id, properties=_flatten(e.model_dump()))


def knowledge_to_node(k: Knowledge) -> Node:
    return Node(
        id=k.id, label="Knowledge", world_id=k.world_id, properties=_flatten(k.model_dump())
    )


def wikiprior_to_node(p: WikiPrior) -> Node:
    return Node(
        id=p.id, label="WikiPrior", world_id=p.world_id, properties=_flatten(p.model_dump())
    )


# --------------------------------------------------------------------------- #
# Edges
# --------------------------------------------------------------------------- #
def contains_edges(regions: list[Region]) -> list[Edge]:
    return [
        Edge(type="CONTAINS", source_id=r.parent_id, target_id=r.id, world_id=r.world_id)
        for r in regions
        if r.parent_id
    ]


def connection_edges(connections: list[ConnectionEdge]) -> list[Edge]:
    return [
        Edge(
            type="CONNECTED_TO",
            source_id=c.source_region_id,
            target_id=c.target_region_id,
            world_id=c.world_id,
            properties=_flatten(
                {
                    "kind": c.kind,
                    "weight": c.weight,
                    "rationale": c.rationale,
                    "wiki_prior_ref": c.wiki_prior_ref,
                }
            ),
        )
        for c in connections
    ]


def scope_edges(scopes: list[ScopeLink]) -> list[Edge]:
    return [
        Edge(
            type="SCOPED_TO",
            source_id=s.knowledge_id,
            target_id=s.region_id,
            world_id=s.world_id,
            properties={
                "scope_type": s.scope_type,
                "confidence": s.confidence,
                "is_rumor": s.is_rumor,
            },
        )
        for s in scopes
    ]


def about_edges(knowledge: list[Knowledge]) -> list[Edge]:
    edges: list[Edge] = []
    for k in knowledge:
        for eid in k.about_entity_ids:
            edges.append(Edge(type="ABOUT", source_id=k.id, target_id=eid, world_id=k.world_id))
    return edges


def derived_from_edges(knowledge: list[Knowledge]) -> list[Edge]:
    edges: list[Edge] = []
    for k in knowledge:
        for pid in k.derived_from_prior_ids:
            edges.append(
                Edge(type="DERIVED_FROM", source_id=k.id, target_id=pid, world_id=k.world_id)
            )
    return edges


def located_in_edges(entities: list[Entity]) -> list[Edge]:
    """LOCATED_IN edges (entity -> region) for entities with a resolved region (BR-B5)."""
    return [
        Edge(type="LOCATED_IN", source_id=e.id, target_id=e.located_in, world_id=e.world_id)
        for e in entities
        if e.located_in
    ]


def relation_edges(relations: list[Relation]) -> list[Edge]:
    return [
        Edge(
            type="RELATED_TO",
            source_id=r.source_id,
            target_id=r.target_id,
            world_id=r.world_id,
            properties={"relation_type": r.relation_type, "confidence": r.confidence},
        )
        for r in relations
    ]


def prior_link_edges(links: list[WikiPriorLink]) -> list[Edge]:
    return [
        Edge(
            type="PRIOR_RELATED_TO",
            source_id=link.source_id,
            target_id=link.target_id,
            world_id=link.world_id,
            properties={
                "relation": link.relation,
                "weight": link.weight,
                "cross_domain": link.cross_domain,
            },
        )
        for link in links
    ]


# --------------------------------------------------------------------------- #
# Search docs (embedding filled by caller)
# --------------------------------------------------------------------------- #
def knowledge_doc(k: Knowledge) -> SearchDoc:
    text = f"{k.title} {k.statement}" + (f" {k.topic}" if k.topic else "")  # BR-A3
    return SearchDoc(
        id=k.id,
        world_id=k.world_id,
        label="Knowledge",
        text=text.strip(),
        meta={"is_global": k.is_global, "confidence": k.confidence, "title": k.title},
    )


def entity_doc(e: Entity) -> SearchDoc:
    return SearchDoc(
        id=e.id,
        world_id=e.world_id,
        label="Entity",
        text=e.name + (f" {e.description}" if e.description else ""),
        meta={"entity_type": e.entity_type},
    )


# --------------------------------------------------------------------------- #
# Reverse: storage Node/Edge -> domain models (U8 WorldLoader)
# --------------------------------------------------------------------------- #
def _provenance(props: dict) -> Provenance:
    return Provenance(
        source=props.get("prov_source", "input"),
        generated_by=props.get("prov_generated_by"),
        note=props.get("prov_note"),
    )


def _json_field(props: dict, key: str, default):
    val = props.get(key, default)
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (ValueError, TypeError):
            return default
    return val if val is not None else default


def node_to_region(node: Node) -> Region:
    p = node.properties
    position = _json_field(p, "position", None)
    return Region(
        id=p["id"],
        world_id=node.world_id,
        name=p["name"],
        level=p["level"],
        parent_id=p.get("parent_id"),
        description=p.get("description"),
        attributes=_json_field(p, "attributes", {}),
        position=position if position else None,
        provenance=_provenance(p),
    )


def node_to_entity(node: Node) -> Entity:
    p = node.properties
    return Entity(
        id=p["id"],
        world_id=node.world_id,
        name=p["name"],
        entity_type=p["entity_type"],
        description=p.get("description"),
        confidence=p.get("confidence", 1.0),
        located_in=p.get("located_in"),
        provenance=_provenance(p),
    )


def node_to_knowledge(node: Node) -> Knowledge:
    p = node.properties
    return Knowledge(
        id=p["id"],
        world_id=node.world_id,
        statement=p["statement"],
        title=p.get("title") or fallback_title(p["statement"]),
        topic=p.get("topic"),
        confidence=p.get("confidence", 1.0),
        is_global=p.get("is_global", False),
        region_hint=p.get("region_hint"),
        about_entity_ids=p.get("about_entity_ids", []),
        derived_from_prior_ids=p.get("derived_from_prior_ids", []),
        provenance=_provenance(p),
    )


def node_to_wikiprior(node: Node) -> WikiPrior:
    p = node.properties
    return WikiPrior(
        id=p["id"],
        world_id=node.world_id,
        prior_type=p["prior_type"],
        condition=p["condition"],
        effect=p["effect"],
        domains=_json_field(p, "domains", []),
        description=p.get("description"),
        confidence=p.get("confidence", 1.0),
        provenance=_provenance(p),
    )


def edge_to_prior_link(edge: Edge) -> WikiPriorLink:
    p = edge.properties
    return WikiPriorLink(
        world_id=edge.world_id,
        source_id=edge.source_id,
        target_id=edge.target_id,
        relation=p.get("relation", "related"),
        weight=p.get("weight", 0.5),
        cross_domain=p.get("cross_domain", False),
        provenance=Provenance(source="input", generated_by="wiki-linker"),
    )


def edge_to_connection(edge: Edge) -> ConnectionEdge:
    p = edge.properties
    return ConnectionEdge(
        world_id=edge.world_id,
        source_region_id=edge.source_id,
        target_region_id=edge.target_id,
        kind=p.get("kind", "adjacent"),
        weight=p.get("weight", 0.5),
        rationale=p.get("rationale"),
        wiki_prior_ref=p.get("wiki_prior_ref"),
        provenance=Provenance(source="input", generated_by="topology"),
    )


def edge_to_scope(edge: Edge) -> ScopeLink:
    p = edge.properties
    return ScopeLink(
        world_id=edge.world_id,
        knowledge_id=edge.source_id,
        region_id=edge.target_id,
        is_rumor=p.get("is_rumor", False),
        scope_type=p.get("scope_type", "direct"),
        confidence=p.get("confidence", 1.0),
    )


def wikiprior_doc(p: WikiPrior) -> SearchDoc:
    return SearchDoc(
        id=p.id,
        world_id=p.world_id,
        label="WikiPrior",
        text=f"{p.condition} {p.effect} {p.description or ''}".strip(),
        meta={
            "prior_type": p.prior_type,
            "condition": p.condition,
            "effect": p.effect,
            "domains": [str(d) for d in p.domains],
            "description": p.description,
            "confidence": p.confidence,
        },
    )
