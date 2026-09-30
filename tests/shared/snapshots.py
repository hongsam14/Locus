"""Snapshot helpers for tests (PBT-07 style utility shared by every boundary's tests)."""

from __future__ import annotations

from locus.shared.models import NPC, KnowledgeGraph, RegionTopology, WorldMeta, WorldSnapshot


def snapshot_of(
    kg: KnowledgeGraph,
    topo: RegionTopology,
    *,
    npcs: list[NPC] | None = None,
    meta: WorldMeta | None = None,
) -> WorldSnapshot:
    return WorldSnapshot(world_id=topo.world_id, meta=meta, kg=kg, topo=topo, npcs=npcs or [])


class StaticSnapshots:
    """A ``SnapshotSource`` that always returns the same snapshot (any world id)."""

    def __init__(self, snapshot: WorldSnapshot) -> None:
        self.snapshot = snapshot
        self.calls = 0

    def get(self, world_id: str) -> WorldSnapshot:
        self.calls += 1
        return self.snapshot
