"""WorldFileImporter — World File -> graph (U2 W9, BR-U2-4/5/11).

Remap when the file's world is not the target (or when forced), validate
references, back the old world up, replace it, persist every section and the
``WorldMeta``, and invalidate the cache in ``finally``. Open-session handling
belongs to the API/CLI layer (world never imports play).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from locus.knowledge.cache import SnapshotCache
from locus.shared.llm.base import EmbeddingProvider
from locus.shared.models import BuildWarning, ImportReport, WorldMeta
from locus.shared.storage.base import GraphRepository, SearchRepository
from locus.shared.storage.persistence import persist_graph
from locus.world.build import WorldExistsError
from locus.world.worldfile.export import WorldFileExporter, to_json_bytes
from locus.world.worldfile.remap import remap_ids, set_world_id, validate_references
from locus.world.worldfile.schema import FORMAT_VERSION, WorldFile

logger = logging.getLogger(__name__)


class WorldFileImporter:
    def __init__(
        self,
        graph: GraphRepository,
        search: SearchRepository,
        embedding: EmbeddingProvider | None,
        cache: SnapshotCache,
        *,
        exporter: WorldFileExporter | None = None,
        backup_dir: Path | None = None,
    ) -> None:
        self._graph = graph
        self._search = search
        self._embedding = embedding
        self._cache = cache
        self._exporter = exporter
        self._backup_dir = backup_dir

    def import_(
        self,
        world_id: str,
        file: WorldFile,
        *,
        replace: bool = True,
        force_remap: bool = False,
    ) -> ImportReport:
        source_world_id = file.world.id
        remapped = force_remap or source_world_id != world_id
        file = remap_ids(file, world_id) if remapped else set_world_id(file, world_id)
        file, warnings = validate_references(file)

        exists = world_id in self._graph.list_world_ids()
        if exists and not replace:
            raise WorldExistsError(f"world already exists: {world_id}")

        replaced = False
        backup_path: Path | None = None
        try:
            if exists:
                backup_path = self._backup(world_id, warnings)
                self._graph.delete_world(world_id)
                replaced = True  # the graph is gone from here on, whatever happens next
                self._cache.invalidate(world_id)
                self._search.delete_world(world_id)
            persist_graph(
                self._graph,
                self._search,
                self._embedding,
                world_id,
                regions=file.regions,
                entities=file.entities,
                knowledge=file.knowledge,
                priors=file.priors,
                prior_links=file.prior_links,
                connections=file.connections,
                scopes=file.scopes,
                relations=file.relations,
                npcs=file.npcs,
                meta=WorldMeta(
                    id=world_id,
                    name=file.world.name,
                    description=file.world.description,
                    format_version=FORMAT_VERSION,
                    last_writer="import",
                ),
                warnings=warnings,
            )
        except Exception as exc:  # e.g. search.delete_world failing after the graph delete
            logger.exception("import commit failed for %s", world_id)
            warnings.append(
                BuildWarning(
                    stage="commit",
                    severity="error",
                    message=f"commit failed after {'replacing' if replaced else 'preparing'} "
                    f"the world: {exc}"
                    + (f"; restore from backup {backup_path}" if backup_path else ""),
                )
            )
        finally:
            self._cache.invalidate(world_id)

        return ImportReport(
            world_id=world_id,
            format_version=file.format_version,
            source_world_id=source_world_id,
            remapped=remapped,
            forced=force_remap,
            replaced=replaced,
            backup_path=str(backup_path) if backup_path else None,
            counts=file.counts(),
            warnings=warnings,
        )

    def _backup(self, world_id: str, warnings: list[BuildWarning]) -> Path | None:
        if self._exporter is None or self._backup_dir is None:
            return None
        try:
            self._backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
            path = self._backup_dir / f"{world_id}-{stamp}-{uuid.uuid4().hex[:6]}.world.json"
            path.write_bytes(to_json_bytes(self._exporter.export(world_id)))
            return path
        except Exception as exc:
            warnings.append(BuildWarning(stage="backup", message=f"backup skipped: {exc}"))
            logger.warning("world backup failed for %s: %s", world_id, exc)
            return None
