"""Storage ports (Repository pattern, AD-Q5=A) + generic graph DTOs.

Core modules depend on these Protocols; Neo4j / OpenSearch adapters implement
them. All operations are scoped by ``world_id`` (BR-17/19).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from ..models import SearchDoc, SearchHit


# --------------------------------------------------------------------------- #
# Generic graph DTOs (infra-level, decoupled from domain models)
# --------------------------------------------------------------------------- #
class Node(BaseModel):
    """A generic graph node for persistence."""

    id: str
    label: str  # e.g. "Region", "Entity", "Knowledge", "Rumor", "WikiPrior"
    world_id: str
    properties: dict = Field(default_factory=dict)


class Edge(BaseModel):
    """A generic graph relationship for persistence."""

    type: str  # e.g. "CONTAINS", "CONNECTED_TO", "SCOPED_TO", "DISTORTED_FROM"
    source_id: str
    target_id: str
    world_id: str
    properties: dict = Field(default_factory=dict)


class TraversalSpec(BaseModel):
    """Constraints for a weighted topology traversal."""

    edge_types: list[str] = Field(default_factory=lambda: ["CONNECTED_TO"])
    max_depth: int = 3
    min_weight: float = 0.0


class Path(BaseModel):
    """A traversal result: ordered node ids and accumulated weight."""

    node_ids: list[str]
    total_weight: float = 1.0


# --------------------------------------------------------------------------- #
# Ports
# --------------------------------------------------------------------------- #
@runtime_checkable
class GraphRepository(Protocol):
    """Graph persistence + traversal (Neo4j adapter)."""

    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def health_check(self) -> bool: ...

    def ensure_schema(self) -> None: ...
    def upsert_nodes(self, nodes: list[Node]) -> None: ...
    def upsert_edges(self, edges: list[Edge]) -> None: ...
    def get_node(self, world_id: str, node_id: str) -> Node | None: ...
    def find_nodes(self, world_id: str, label: str, filters: dict | None = None) -> list[Node]: ...
    def get_region_subtree(self, world_id: str, region_id: str) -> list[Node]: ...
    def get_region_ancestors(self, world_id: str, region_id: str) -> list[Node]: ...
    def get_edges(self, world_id: str, types: list[str] | None = None) -> list[Edge]: ...
    def traverse(self, world_id: str, start_id: str, spec: TraversalSpec) -> list[Path]: ...
    def delete_node(self, world_id: str, node_id: str) -> None: ...
    def delete_world(self, world_id: str) -> None: ...


@runtime_checkable
class SearchRepository(Protocol):
    """Hybrid (BM25 + kNN) search persistence (OpenSearch adapter)."""

    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def health_check(self) -> bool: ...

    def ensure_index(self) -> None: ...
    def index(self, docs: list[SearchDoc]) -> None: ...
    def hybrid_search(
        self,
        world_id: str | None,
        query_text: str,
        query_embedding: list[float] | None = None,
        k: int = 5,
        filters: dict | None = None,
    ) -> list[SearchHit]: ...  # world_id=None -> search across all worlds (designer cross-world)
    def delete_world(self, world_id: str) -> None: ...
