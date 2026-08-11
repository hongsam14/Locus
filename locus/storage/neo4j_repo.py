"""Neo4j implementation of GraphRepository (US-9.1).

Idempotent MERGE-based upserts, world_id scoping, weighted traversal. The
``neo4j`` driver is imported lazily so the module can be imported (and query
construction unit-tested) without the package or a live database.
"""

from __future__ import annotations

import re

from .base import Edge, GraphRepository, Node, Path, TraversalSpec

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_ident(value: str) -> str:
    """Validate a Cypher label / relationship type (cannot be parameterized)."""
    if not _IDENT_RE.match(value):
        raise ValueError(f"Unsafe Cypher identifier: {value!r}")
    return value


class Neo4jGraphRepository(GraphRepository):
    def __init__(self, *, uri: str, user: str, password: str) -> None:
        self._uri = uri
        self._auth = (user, password)
        self._driver = None

    # -- lifecycle -------------------------------------------------------- #
    def connect(self) -> None:
        from neo4j import GraphDatabase

        self._driver = GraphDatabase.driver(self._uri, auth=self._auth)
        self._driver.verify_connectivity()

    def disconnect(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def health_check(self) -> bool:
        if self._driver is None:
            return False
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def _run(self, query: str, params: dict) -> list[dict]:
        if self._driver is None:
            raise RuntimeError("Neo4jGraphRepository not connected; call connect() first.")
        with self._driver.session() as session:
            result = session.run(query, **params)
            return [record.data() for record in result]

    # -- schema ----------------------------------------------------------- #
    NODE_LABELS = ("Region", "Entity", "Relation", "Knowledge", "WikiPrior")

    def ensure_schema(self) -> None:
        """Create uniqueness constraints + world_id indexes (idempotent).

        World nodes are not persisted (CL-A1=A); every label is keyed by id and
        partitioned by world_id.
        """
        for label in self.NODE_LABELS:
            self._run(
                f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.id IS UNIQUE",
                {},
            )
            self._run(
                f"CREATE INDEX {label.lower()}_world IF NOT EXISTS "
                f"FOR (n:{label}) ON (n.world_id)",
                {},
            )

    # -- writes ----------------------------------------------------------- #
    def upsert_nodes(self, nodes: list[Node]) -> None:
        for node in nodes:
            label = _safe_ident(node.label)
            query = f"MERGE (n:{label} {{id: $id, world_id: $world_id}}) " f"SET n += $props"
            self._run(query, {"id": node.id, "world_id": node.world_id, "props": node.properties})

    def upsert_edges(self, edges: list[Edge]) -> None:
        for edge in edges:
            rel = _safe_ident(edge.type)
            query = (
                "MATCH (a {id: $source_id, world_id: $world_id}) "
                "MATCH (b {id: $target_id, world_id: $world_id}) "
                f"MERGE (a)-[r:{rel}]->(b) "
                "SET r += $props"
            )
            self._run(
                query,
                {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "world_id": edge.world_id,
                    "props": edge.properties,
                },
            )

    # -- reads ------------------------------------------------------------ #
    def get_node(self, world_id: str, node_id: str) -> Node | None:
        rows = self._run(
            "MATCH (n {id: $id, world_id: $world_id}) "
            "RETURN labels(n) AS labels, properties(n) AS props LIMIT 1",
            {"id": node_id, "world_id": world_id},
        )
        if not rows:
            return None
        return self._to_node(rows[0], world_id)

    def find_nodes(self, world_id: str, label: str, filters: dict | None = None) -> list[Node]:
        safe = _safe_ident(label)
        where = ["n.world_id = $world_id"]
        params: dict = {"world_id": world_id}
        for key, val in (filters or {}).items():
            _safe_ident(key)
            where.append(f"n.{key} = ${key}")
            params[key] = val
        query = (
            f"MATCH (n:{safe}) WHERE {' AND '.join(where)} "
            "RETURN labels(n) AS labels, properties(n) AS props"
        )
        return [self._to_node(r, world_id) for r in self._run(query, params)]

    def get_region_subtree(self, world_id: str, region_id: str) -> list[Node]:
        query = (
            "MATCH (r:Region {id: $id, world_id: $world_id}) "
            "MATCH (r)-[:CONTAINS*0..]->(c:Region) "
            "RETURN DISTINCT labels(c) AS labels, properties(c) AS props"
        )
        return [
            self._to_node(r, world_id)
            for r in self._run(query, {"id": region_id, "world_id": world_id})
        ]

    def get_region_ancestors(self, world_id: str, region_id: str) -> list[Node]:
        query = (
            "MATCH (a:Region)-[:CONTAINS*1..]->(r:Region {id: $id, world_id: $world_id}) "
            "WHERE a.world_id = $world_id "
            "RETURN DISTINCT labels(a) AS labels, properties(a) AS props"
        )
        return [
            self._to_node(r, world_id)
            for r in self._run(query, {"id": region_id, "world_id": world_id})
        ]

    def traverse(self, world_id: str, start_id: str, spec: TraversalSpec) -> list[Path]:
        rel_types = "|".join(_safe_ident(t) for t in spec.edge_types)
        query = (
            f"MATCH p = (s {{id: $id, world_id: $world_id}})-[rels:{rel_types}*1..{int(spec.max_depth)}]->(e) "
            "WHERE ALL(r IN rels WHERE coalesce(r.weight, 1.0) >= $min_weight) "
            "RETURN [n IN nodes(p) | n.id] AS node_ids, "
            "reduce(w = 1.0, r IN rels | w * coalesce(r.weight, 1.0)) AS total_weight"
        )
        rows = self._run(
            query, {"id": start_id, "world_id": world_id, "min_weight": spec.min_weight}
        )
        return [Path(node_ids=r["node_ids"], total_weight=r["total_weight"]) for r in rows]

    def get_edges(self, world_id: str, types: list[str] | None = None) -> list[Edge]:
        type_filter = ""
        if types:
            for t in types:
                _safe_ident(t)
            type_filter = "WHERE type(r) IN $types "
        query = (
            "MATCH (a {world_id: $world_id})-[r]->(b {world_id: $world_id}) "
            f"{type_filter}"
            "RETURN type(r) AS type, a.id AS source_id, b.id AS target_id, properties(r) AS props"
        )
        params: dict = {"world_id": world_id}
        if types:
            params["types"] = types
        rows = self._run(query, params)
        return [
            Edge(
                type=row["type"],
                source_id=row["source_id"],
                target_id=row["target_id"],
                world_id=world_id,
                properties=dict(row.get("props") or {}),
            )
            for row in rows
        ]

    def delete_node(self, world_id: str, node_id: str) -> None:
        self._run(
            "MATCH (n {id: $id, world_id: $world_id}) DETACH DELETE n",
            {"id": node_id, "world_id": world_id},
        )

    def delete_world(self, world_id: str) -> None:
        self._run("MATCH (n {world_id: $world_id}) DETACH DELETE n", {"world_id": world_id})

    # -- helpers ---------------------------------------------------------- #
    @staticmethod
    def _to_node(row: dict, world_id: str) -> Node:
        props = dict(row["props"])
        labels = row["labels"]
        label = labels[0] if labels else "Node"
        node_id = props.get("id", "")
        return Node(id=node_id, label=label, world_id=world_id, properties=props)
