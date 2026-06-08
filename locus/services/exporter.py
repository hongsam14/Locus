"""Exporter — serialize a world graph to a JSON-able dict (U9, Q4=A)."""

from __future__ import annotations

from ..query.loader import WorldLoader


class Exporter:
    def __init__(self, loader: WorldLoader) -> None:
        self._loader = loader

    def export_world(self, world_id: str) -> dict:
        kg, topo = self._loader.load(world_id)
        return {
            "world_id": world_id,
            "regions": [r.model_dump() for r in topo.regions],
            "connections": [c.model_dump() for c in topo.connections],
            "entities": [e.model_dump() for e in kg.entities],
            "knowledge": [k.model_dump() for k in kg.knowledge],
            "rumors": [r.model_dump() for r in kg.rumors],
            "scopes": [s.model_dump() for s in kg.scopes],
        }
