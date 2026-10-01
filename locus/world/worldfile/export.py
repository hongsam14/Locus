"""WorldFileExporter — snapshot -> World File v1 with deterministic ordering (U2 W9, BR-U2-3)."""

from __future__ import annotations

from datetime import UTC, datetime

from locus.knowledge.cache import SnapshotSource
from locus.shared.models import WorldMeta
from locus.world.worldfile.schema import FORMAT_VERSION, WorldFile, WorldFileMeta


def sort_sections(file: WorldFile) -> WorldFile:
    """Apply the canonical sort keys (BLM §6) so equal worlds give equal files."""
    return file.model_copy(
        update={
            "regions": sorted(file.regions, key=lambda r: r.id),
            "connections": sorted(
                file.connections,
                key=lambda c: (c.source_region_id, c.target_region_id, str(c.kind)),
            ),
            "entities": sorted(file.entities, key=lambda e: e.id),
            "relations": sorted(file.relations, key=lambda r: r.id),
            "knowledge": sorted(file.knowledge, key=lambda k: k.id),
            "scopes": sorted(file.scopes, key=lambda s: (s.knowledge_id, s.region_id)),
            "priors": sorted(file.priors, key=lambda p: p.id),
            "prior_links": sorted(
                file.prior_links, key=lambda link: (link.source_id, link.target_id, link.relation)
            ),
            "npcs": sorted(file.npcs, key=lambda n: n.id),
            "event_seeds": sorted(file.event_seeds, key=lambda s: s.id),
        }
    )


def to_json_bytes(file: WorldFile) -> bytes:
    return file.to_json().encode("utf-8")


class WorldFileExporter:
    def __init__(self, snapshots: SnapshotSource) -> None:
        self._snapshots = snapshots

    def export(self, world_id: str) -> WorldFile:
        s = self._snapshots.get(world_id)
        meta = s.meta or WorldMeta(id=world_id, name=world_id)
        return sort_sections(
            WorldFile(
                format_version=FORMAT_VERSION,
                world=WorldFileMeta(id=world_id, name=meta.name, description=meta.description),
                exported_at=datetime.now(UTC),
                regions=s.topo.regions,
                connections=s.topo.connections,
                entities=s.kg.entities,
                relations=s.kg.relations,
                knowledge=s.kg.knowledge,
                scopes=s.kg.scopes,
                priors=s.kg.priors,
                prior_links=s.kg.prior_links,
                npcs=s.npcs,
                event_seeds=s.event_seeds,
            )
        )

    def export_world(self, world_id: str) -> dict:
        """Compatibility dict for ``GET /worlds/{w}/export``: the v1 file plus the
        legacy top-level ``world_id`` (the web client reads it)."""
        data = self.export(world_id).model_dump(mode="json")
        data["world_id"] = world_id
        return data
