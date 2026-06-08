"""QueryEngine — region knowledge + shared/unique diff (U8, FR-H)."""

from __future__ import annotations

from ..consensus.engine import DEFAULT_PARAMS, ConsensusEngine, ConsensusParams
from ..models import ConsensusView, KnowledgeView, QueryResult, RegionDiff
from .loader import WorldLoader


def view_items(view: ConsensusView, include_rumors: bool = True) -> list[KnowledgeView]:
    items = view.direct + view.inherited + view.global_knowledge + view.propagated
    if include_rumors:
        items = items + view.rumors
    return items


def split_shared_unique(
    view: ConsensusView, include_rumors: bool = True
) -> tuple[list[str], list[str]]:
    """unique = direct (region-specific); shared = inherited+global+propagated(+rumors). Pure."""
    unique = [v.knowledge_id for v in view.direct]
    shared_views = view.inherited + view.global_knowledge + view.propagated
    if include_rumors:
        shared_views = shared_views + view.rumors
    return unique, [v.knowledge_id for v in shared_views]


def diff_sets(ids_a: set[str], ids_b: set[str]) -> tuple[list[str], list[str], list[str]]:
    """Return (shared, only_a, only_b). Pure."""
    return sorted(ids_a & ids_b), sorted(ids_a - ids_b), sorted(ids_b - ids_a)


class QueryEngine:
    def __init__(self, loader: WorldLoader, params: ConsensusParams = DEFAULT_PARAMS) -> None:
        self._loader = loader
        self._params = params

    def knowledge_for_region(
        self, world_id: str, region_id: str, *, include_rumors: bool = True
    ) -> QueryResult:
        kg, topo = self._loader.load(world_id)
        if region_id not in {r.id for r in topo.regions}:
            raise LookupError(f"region not found: {region_id}")
        view = ConsensusEngine(kg, topo, self._params).resolve(region_id)
        items = view_items(view, include_rumors)
        unique, shared = split_shared_unique(view, include_rumors)
        return QueryResult(
            world_id=world_id,
            region_id=region_id,
            items=items,
            shared_ids=shared,
            unique_ids=unique,
        )

    def diff_regions(self, world_id: str, region_a: str, region_b: str) -> RegionDiff:
        kg, topo = self._loader.load(world_id)
        ids = {r.id for r in topo.regions}
        if region_a not in ids or region_b not in ids:
            raise LookupError("region not found")
        engine = ConsensusEngine(kg, topo, self._params)
        items_a = {v.knowledge_id for v in view_items(engine.resolve(region_a))}
        items_b = {v.knowledge_id for v in view_items(engine.resolve(region_b))}
        shared, only_a, only_b = diff_sets(items_a, items_b)
        return RegionDiff(
            world_id=world_id,
            region_a=region_a,
            region_b=region_b,
            shared_ids=shared,
            only_a_ids=only_a,
            only_b_ids=only_b,
        )
