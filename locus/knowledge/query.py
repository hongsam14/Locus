"""QueryEngine — region knowledge, shared/unique diff, region briefs (U8 FR-H, U2 K5)."""

from __future__ import annotations

from locus.knowledge.cache import SnapshotSource
from locus.knowledge.consensus import DEFAULT_PARAMS, ConsensusEngine, ConsensusParams
from locus.shared.models import (
    ConsensusView,
    KnowledgeView,
    QueryResult,
    Region,
    RegionBrief,
    RegionDiff,
    ScopeType,
    WorldSnapshot,
)
from locus.shared.models.util import rank_of


def view_items(view: ConsensusView, include_hearsay: bool = True) -> list[KnowledgeView]:
    items = view.direct + view.inherited + view.global_knowledge + view.propagated
    if include_hearsay:
        items = items + view.hearsay
    return items


def region_known(view: ConsensusView) -> list[KnowledgeView]:
    """Knowledge a region's inhabitants genuinely know = direct + inherited + global.

    Excludes distance-based ``propagated`` and ``hearsay``. Pure; used by the
    play layer's region knowledge view and by NPC scoping."""
    return view.direct + view.inherited + view.global_knowledge


def split_shared_unique(
    view: ConsensusView, include_hearsay: bool = True
) -> tuple[list[str], list[str]]:
    """unique = direct (region-specific); shared = inherited+global+propagated(+hearsay). Pure."""
    unique = [v.knowledge_id for v in view.direct]
    shared_views = view.inherited + view.global_knowledge + view.propagated
    if include_hearsay:
        shared_views = shared_views + view.hearsay
    return unique, [v.knowledge_id for v in shared_views]


def diff_sets(ids_a: set[str], ids_b: set[str]) -> tuple[list[str], list[str], list[str]]:
    """Return (shared, only_a, only_b). Pure."""
    return sorted(ids_a & ids_b), sorted(ids_a - ids_b), sorted(ids_b - ids_a)


def level_path(region: Region, snapshot: WorldSnapshot) -> list[str]:
    """Names from the top ancestor down to ``region`` (cycle-safe). Pure."""
    names = [region.name]
    seen = {region.id}
    cur = region
    while cur.parent_id and cur.parent_id not in seen:
        parent = snapshot.regions_by_id.get(cur.parent_id)
        if parent is None:
            break
        seen.add(parent.id)
        names.append(parent.name)
        cur = parent
    return list(reversed(names))


def region_briefs(snapshot: WorldSnapshot, *, top_k: int = 3) -> list[RegionBrief]:
    """One prompt-ready brief per region (BR-U2-20): hierarchy path, description and
    the ``top_k`` DIRECT knowledge titles by confidence (ties by id). Pure."""
    by_id = {k.id: k for k in snapshot.kg.knowledge}
    direct: dict[str, list[tuple[float, str]]] = {}
    for s in snapshot.kg.scopes:
        if str(s.scope_type) == ScopeType.DIRECT.value and s.knowledge_id in by_id:
            direct.setdefault(s.region_id, []).append((s.confidence, s.knowledge_id))
    out: list[RegionBrief] = []
    for r in sorted(
        snapshot.topo.regions,
        key=lambda x: (rank_of(x.level) if rank_of(x.level) is not None else 99, x.name, x.id),
    ):
        ranked = sorted(direct.get(r.id, []), key=lambda t: (-t[0], t[1]))[:top_k]
        out.append(
            RegionBrief(
                region_id=r.id,
                name=r.name,
                level=str(r.level),
                level_path=level_path(r, snapshot),
                description=r.description,
                top_knowledge=[by_id[kid].title for _, kid in ranked],
            )
        )
    return out


class QueryEngine:
    """Canonical region knowledge served from a ``SnapshotSource`` (the ``WorldCache``)."""

    def __init__(self, cache: SnapshotSource, params: ConsensusParams = DEFAULT_PARAMS) -> None:
        self._cache = cache
        self._params = params

    def knowledge_for_region(
        self, world_id: str, region_id: str, *, include_hearsay: bool = True
    ) -> QueryResult:
        snapshot = self._cache.get(world_id)
        if region_id not in snapshot.regions_by_id:
            raise LookupError(f"region not found: {region_id}")
        view = ConsensusEngine.from_snapshot(snapshot, self._params).resolve(region_id)
        items = view_items(view, include_hearsay)
        unique, shared = split_shared_unique(view, include_hearsay)
        return QueryResult(
            world_id=world_id,
            region_id=region_id,
            items=items,
            shared_ids=shared,
            unique_ids=unique,
        )

    def diff_regions(self, world_id: str, region_a: str, region_b: str) -> RegionDiff:
        snapshot = self._cache.get(world_id)
        ids = snapshot.regions_by_id
        if region_a not in ids or region_b not in ids:
            raise LookupError("region not found")
        engine = ConsensusEngine.from_snapshot(snapshot, self._params)
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

    def region_briefs(self, world_id: str, *, top_k: int = 3) -> list[RegionBrief]:
        return region_briefs(self._cache.get(world_id), top_k=top_k)
