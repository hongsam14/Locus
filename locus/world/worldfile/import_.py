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
from locus.world.build import BackupFailedError, WorldExistsError, backup_failed_warning
from locus.world.worldfile.export import WorldFileExporter, to_json_bytes
from locus.world.worldfile.remap import (
    duplicate_ids,
    merge_scopes,
    remap_ids,
    set_world_id,
    validate_references,
)
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
        exists = world_id in self._graph.list_world_ids()
        if exists and not replace:
            raise WorldExistsError(f"world already exists: {world_id}")
        # Before anything is written, and on the file's own ids so the message names what
        # the designer must fix; a remap maps each id to one new id, so the answer is the
        # same either way (V7 code review #12).
        twice = duplicate_ids(file)
        file = remap_ids(file, world_id) if remapped else set_world_id(file, world_id)
        if twice:
            return self._stopped(
                world_id, file, source_world_id, remapped, force_remap, [_duplicates(twice)]
            )
        file, warnings = validate_references(file)
        file = merge_scopes(file)

        replaced = False
        backup_path: Path | None = None
        try:
            if exists:
                try:
                    backup_path = self._backup(world_id)
                except BackupFailedError as exc:  # before anything is deleted (V7, R-07)
                    warnings.append(backup_failed_warning(exc))
                    return self._stopped(
                        world_id, file, source_world_id, remapped, force_remap, warnings
                    )
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
                seeds=file.event_seeds,
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

    @staticmethod
    def _stopped(
        world_id: str,
        file: WorldFile,
        source_world_id: str,
        remapped: bool,
        forced: bool,
        warnings: list[BuildWarning],
    ) -> ImportReport:
        """An import stopped before anything was deleted or written: the old world stays
        (V7 — duplicate ids, BR-V7-17; a failed backup, BR-V7-10)."""
        return ImportReport(
            world_id=world_id,
            format_version=file.format_version,
            source_world_id=source_world_id,
            remapped=remapped,
            forced=forced,
            counts=file.counts(),
            warnings=warnings,
        )

    def _backup(self, world_id: str) -> Path | None:
        """``None`` when no backup is set up; ``BackupFailedError`` when one is set up and
        could not be written (V7, BR-V7-10)."""
        if self._exporter is None or self._backup_dir is None:
            return None
        try:
            self._backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
            path = self._backup_dir / f"{world_id}-{stamp}-{uuid.uuid4().hex[:6]}.world.json"
            path.write_bytes(to_json_bytes(self._exporter.export(world_id)))
            return path
        except Exception as exc:
            logger.warning("world backup failed for %s: %s", world_id, exc)
            raise BackupFailedError(str(exc)) from exc


def _duplicates(twice: list[str]) -> BuildWarning:
    shown = ", ".join(twice[:10]) + (f" and {len(twice) - 10} more" if len(twice) > 10 else "")
    return BuildWarning(
        stage="duplicate-ids",
        severity="error",
        message=f"duplicate ids in the World File: {shown}",
    )
