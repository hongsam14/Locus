"""WorldLoader — read one world from the graph into a ``WorldSnapshot`` (U2 K3).

Reads Region / Entity / Knowledge / WikiPrior / NPC / WorldMeta nodes and the
CONNECTED_TO / SCOPED_TO / RELATED_TO / PRIOR_RELATED_TO / LIVES_IN edges. A node
or edge that fails to map is skipped and reported in ``load_warnings`` instead of
breaking the whole world (BR-U2-16). An empty world raises ``LookupError``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar

from locus.shared.models import (
    NPC,
    BuildWarning,
    KnowledgeGraph,
    RegionTopology,
    WorldMeta,
    WorldSnapshot,
)
from locus.shared.storage import graph_mapping as gm
from locus.shared.storage.base import Edge, GraphRepository, Node

logger = logging.getLogger(__name__)
T = TypeVar("T")


class WorldLoader:
    def __init__(self, graph_repo: GraphRepository) -> None:
        self._g = graph_repo

    def version(self, world_id: str) -> str | None:
        """Cheap change marker: the WorldMeta's ``updated_at``/``last_writer`` (one small
        read). ``None`` for worlds without meta (pre-U2) — invalidation-only for those."""
        metas = self._g.find_nodes(world_id, "WorldMeta")
        if not metas:
            return None
        try:
            meta = gm.node_to_worldmeta(metas[0])
        except Exception:  # pragma: no cover - a broken meta node is reported by load()
            return None
        return f"{meta.updated_at.isoformat()}|{meta.last_writer}"

    def load(self, world_id: str) -> WorldSnapshot:
        warnings: list[BuildWarning] = []

        def nodes(label: str, fn: Callable[[Node], T]) -> list[T]:
            return _map_all(self._g.find_nodes(world_id, label), fn, label, warnings)

        regions = nodes("Region", gm.node_to_region)
        entities = nodes("Entity", gm.node_to_entity)
        knowledge = nodes("Knowledge", gm.node_to_knowledge)
        priors = nodes("WikiPrior", gm.node_to_wikiprior)
        npcs: list[NPC] = nodes("NPC", gm.node_to_npc)
        seeds = nodes("EventSeed", gm.node_to_seed)
        metas: list[WorldMeta] = nodes("WorldMeta", gm.node_to_worldmeta)

        edges = self._g.get_edges(world_id)
        by_type: dict[str, list[Edge]] = {}
        for e in edges:
            by_type.setdefault(e.type, []).append(e)

        connections = _map_all(
            by_type.get("CONNECTED_TO", []), gm.edge_to_connection, "CONNECTED_TO", warnings
        )
        scopes = _map_all(by_type.get("SCOPED_TO", []), gm.edge_to_scope, "SCOPED_TO", warnings)
        relations = _map_all(
            by_type.get("RELATED_TO", []), gm.edge_to_relation, "RELATED_TO", warnings
        )
        prior_links = _map_all(
            by_type.get("PRIOR_RELATED_TO", []), gm.edge_to_prior_link, "PRIOR_RELATED_TO", warnings
        )
        lives_in = {e.source_id: e.target_id for e in by_type.get("LIVES_IN", [])}
        npcs = [
            n.model_copy(update={"home_region_id": lives_in[n.id]}) if n.id in lives_in else n
            for n in npcs
        ]

        if not (regions or entities or knowledge or npcs or priors or metas):
            raise LookupError(f"world not found: {world_id}")

        # edges whose endpoint node was skipped (or never existed) must not reach the
        # snapshot — the export would otherwise carry dangling references (review U2 #9)
        region_ids = {r.id for r in regions}
        entity_ids = {e.id for e in entities}
        knowledge_ids = {k.id for k in knowledge}
        prior_ids = {p.id for p in priors}

        def dangling(what: str, item_id: str) -> None:
            warnings.append(
                BuildWarning(stage="load", item_id=item_id, message=f"{what}: dangling reference")
            )

        connections = _keep(
            connections,
            lambda c: c.source_region_id in region_ids and c.target_region_id in region_ids,
            lambda c: dangling("CONNECTED_TO", f"{c.source_region_id}->{c.target_region_id}"),
        )
        scopes = _keep(
            scopes,
            lambda sc: sc.knowledge_id in knowledge_ids and sc.region_id in region_ids,
            lambda sc: dangling("SCOPED_TO", f"{sc.knowledge_id}@{sc.region_id}"),
        )
        relations = _keep(
            relations,
            lambda r: r.source_id in entity_ids and r.target_id in entity_ids,
            lambda r: dangling("RELATED_TO", r.id),
        )
        prior_links = _keep(
            prior_links,
            lambda pl: pl.source_id in prior_ids and pl.target_id in prior_ids,
            lambda pl: dangling("PRIOR_RELATED_TO", f"{pl.source_id}->{pl.target_id}"),
        )
        npcs = _keep(
            npcs,
            lambda n: n.home_region_id in region_ids,
            lambda n: dangling("NPC home region", n.id),
        )
        seeds = _keep(  # U8: a seed whose region is gone never reaches a session
            seeds,
            lambda s: s.region_id in region_ids,
            lambda s: dangling("EventSeed region", s.id),
        )

        scoped = {s.knowledge_id for s in scopes}
        unscoped = [k.id for k in knowledge if not k.is_global and k.id not in scoped]
        kg = KnowledgeGraph(
            world_id=world_id,
            entities=entities,
            relations=relations,
            knowledge=knowledge,
            scopes=scopes,
            priors=priors,
            prior_links=prior_links,
            unscoped_knowledge_ids=unscoped,
        )
        topo = RegionTopology(world_id=world_id, regions=regions, connections=connections)
        return WorldSnapshot(
            world_id=world_id,
            meta=metas[0] if metas else None,
            kg=kg,
            topo=topo,
            npcs=npcs,
            event_seeds=seeds,
            load_warnings=warnings,
        )


def _keep(items: list, pred: Callable, on_drop: Callable) -> list:
    out = []
    for item in items:
        if pred(item):
            out.append(item)
        else:
            on_drop(item)
    return out


def _map_all(items: list, fn: Callable, what: str, warnings: list[BuildWarning]) -> list:
    out: list = []
    for item in items:
        try:
            out.append(fn(item))
        except Exception as exc:  # one bad node must not poison the world (BR-U2-16)
            item_id = getattr(item, "id", None) or getattr(item, "source_id", None)
            warnings.append(BuildWarning(stage="load", item_id=item_id, message=f"{what}: {exc}"))
            logger.warning("skipped %s %s while loading: %s", what, item_id, exc)
    return out
