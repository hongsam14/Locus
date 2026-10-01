"""Storage ports (Repository pattern, AD-Q5=A) + generic graph DTOs.

Core modules depend on these Protocols; Neo4j / OpenSearch adapters implement
them. All operations are scoped by ``world_id`` (BR-17/19).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from locus.shared.models import SearchDoc, SearchHit


# --------------------------------------------------------------------------- #
# Generic graph DTOs (infra-level, decoupled from domain models)
# --------------------------------------------------------------------------- #
class Node(BaseModel):
    """A generic graph node for persistence."""

    id: str
    label: str  # e.g. "Region", "Entity", "Knowledge", "WikiPrior"
    world_id: str
    properties: dict = Field(default_factory=dict)


class Edge(BaseModel):
    """A generic graph relationship for persistence."""

    type: str  # e.g. "CONTAINS", "CONNECTED_TO", "SCOPED_TO", "LIVES_IN"
    source_id: str
    target_id: str
    world_id: str
    properties: dict = Field(default_factory=dict)


def edge_identity_field(edge: Edge) -> str | None:
    """Which property, besides the endpoints, identifies an edge of this type.

    Relations carry their own ``id`` (two relations of different types between the
    same entities coexist); connections are keyed by ``kind`` (a river and a road
    between two regions coexist). Other edge types are unique per endpoint pair.
    """
    if "id" in edge.properties:
        return "id"
    if edge.type == "CONNECTED_TO" and "kind" in edge.properties:
        return "kind"
    return None


class EdgeKey(BaseModel):
    """One edge to delete (U3, domain-entities §1.1): its type, endpoints and identity.

    ``identity`` holds the properties that tell parallel edges apart, by the same rule
    as :func:`edge_identity_field` (``{"kind": ...}`` for a connection, ``{"id": ...}``
    for a relation). An empty identity matches every edge of the type between the two
    nodes.
    """

    type: str
    source_id: str
    target_id: str
    identity: dict = Field(default_factory=dict)


class ConstraintViolation(RuntimeError):
    """A unique constraint rejected a write (an ``id`` already exists in another world).

    Adapters translate their driver's error into this so callers (World File import)
    can report ``id collision with another world`` without importing a driver (U2 BR-U2-4).
    """


# --------------------------------------------------------------------------- #
# Ports
# --------------------------------------------------------------------------- #
@runtime_checkable
class GraphRepository(Protocol):
    """Graph persistence (Neo4j adapter)."""

    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def health_check(self) -> bool: ...

    def ensure_schema(self) -> None: ...
    def upsert_nodes(self, nodes: list[Node]) -> None: ...
    def upsert_edges(self, edges: list[Edge]) -> None: ...
    def replace_nodes(self, nodes: list[Node]) -> None: ...  # U3: properties replaced whole
    def delete_edges(self, world_id: str, edges: list[EdgeKey]) -> int: ...  # U3
    def get_node(self, world_id: str, node_id: str) -> Node | None: ...
    def find_nodes(self, world_id: str, label: str, filters: dict | None = None) -> list[Node]: ...
    def get_edges(self, world_id: str, types: list[str] | None = None) -> list[Edge]: ...
    def delete_node(self, world_id: str, node_id: str) -> None: ...
    def delete_world(self, world_id: str) -> None: ...
    def list_world_ids(self) -> list[str]: ...


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
    def delete(self, world_id: str, doc_ids: list[str]) -> int: ...  # U3: missing ids are skipped
    def delete_world(self, world_id: str) -> None: ...
