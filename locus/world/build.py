"""WorldBuilder — end-to-end world build (U2 W6; was PipelineOrchestrator).

Prepare, then commit (BR-U2-11, RE A3): ingestion, topology and prior
distillation run without touching the graph, so a failure there leaves an
existing world intact. The commit phase backs the old world up as a World File,
deletes it, persists priors (corroboration reads them back through search),
runs the ontology and persists the rest. The cache is invalidated in ``finally``.

Every build wraps the providers in a fresh ``LLMCallCounter`` and hands the
wrappers to every factory, so the report's call counts are exact and no state is
shared between builds (BR-U2-15, RE A12). Each world self-distills its own
WikiPriors and links them, then builds the ontology against its own single-world
wiki (BR-A9, BR-A12).
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from locus.knowledge.cache import SnapshotCache
from locus.shared.config.tuning import WorldTuning
from locus.shared.llm.base import EmbeddingProvider, LLMProvider, VLMProvider
from locus.shared.llm.counting import LLMCallCounter
from locus.shared.llm.factory import ProviderFactory
from locus.shared.models import (
    BuildReport,
    BuildWarning,
    IngestionResult,
    RegionTopology,
    SourceKind,
    WikiPrior,
    WikiPriorLink,
    WorldMeta,
)
from locus.shared.storage.base import GraphRepository, SearchRepository
from locus.shared.storage.persistence import persist_graph
from locus.world.ingestion.service import IngestionService, WorldInputs
from locus.world.ontology.builder import OntologyBuild, OntologyBuilder
from locus.world.topology.builder import TopologyBuild, TopologyBuilder
from locus.world.wiki.base import WIKI_FALLBACK_MAX, CommonsenseWiki
from locus.world.wiki.distiller import PriorDistiller
from locus.world.wiki.linker import WikiPriorLinker

logger = logging.getLogger(__name__)


class WorldExistsError(RuntimeError):
    """The world already exists and ``replace`` was not requested (409 / exit 1)."""


class BuildInProgressError(RuntimeError):
    """A build of this world is already running in this process (409; U8 review #2). A
    second one would race the first past the existence check and commit a second copy."""


class TopologyBuilderLike(Protocol):
    def build(self, ingestion: IngestionResult, *, world_id: str) -> TopologyBuild: ...


class OntologyBuilderLike(Protocol):
    def build(
        self, ingestion: IngestionResult, topology: RegionTopology, *, world_id: str
    ) -> OntologyBuild: ...


class IngestionLike(Protocol):
    def ingest_all(self, world_id: str, inputs: WorldInputs) -> IngestionResult: ...


class DistillerLike(Protocol):
    def distill(
        self, ingestion: IngestionResult, topology: RegionTopology, *, world_id: str
    ) -> list[WikiPrior]: ...


class LinkerLike(Protocol):
    def link(self, priors: list[WikiPrior], *, world_id: str) -> list[WikiPriorLink]: ...


class ExporterLike(Protocol):
    def export_world(self, world_id: str) -> dict: ...


@dataclass
class BuildProviders:
    llm: LLMProvider | None = None
    vlm: VLMProvider | None = None
    embedding: EmbeddingProvider | None = None


IngestionFactory = Callable[[LLMProvider | None, VLMProvider | None], IngestionLike]
TopologyFactory = Callable[[CommonsenseWiki | None], TopologyBuilderLike]
OntologyFactory = Callable[
    [LLMProvider | None, EmbeddingProvider | None, CommonsenseWiki | None], OntologyBuilderLike
]
WikiFactory = Callable[[str, LLMProvider | None, EmbeddingProvider | None], CommonsenseWiki]
DistillerFactory = Callable[[LLMProvider | None], DistillerLike]
LinkerFactory = Callable[[LLMProvider | None, EmbeddingProvider | None], LinkerLike]


class WorldBuilder:
    def __init__(
        self,
        graph_repo: GraphRepository,
        search_repo: SearchRepository,
        cache: SnapshotCache,
        *,
        providers: BuildProviders,
        ingestion_factory: IngestionFactory,
        topology_factory: TopologyFactory,
        ontology_factory: OntologyFactory,
        wiki_factory: WikiFactory | None = None,
        distiller_factory: DistillerFactory | None = None,
        linker_factory: LinkerFactory | None = None,
        exporter: ExporterLike | None = None,
        backup_dir: Path | None = None,
    ) -> None:
        self._building: set[str] = set()  # world ids with a build running
        self._building_lock = threading.Lock()
        self._graph = graph_repo
        self._search = search_repo
        self._cache = cache
        self._providers = providers
        self._ingestion_factory = ingestion_factory
        self._topology_factory = topology_factory
        self._ontology_factory = ontology_factory
        self._wiki_factory = wiki_factory
        self._distiller_factory = distiller_factory
        self._linker_factory = linker_factory
        self._exporter = exporter
        self._backup_dir = backup_dir

    @classmethod
    def from_factory(
        cls,
        factory: ProviderFactory,
        graph_repo: GraphRepository,
        search_repo: SearchRepository,
        *,
        cache: SnapshotCache,
        exporter: ExporterLike | None = None,
        backup_dir: Path | None = None,
        tuning: WorldTuning,
    ) -> WorldBuilder:
        # The weight table and the dedup bar (U7, FR-A7). Required: a composition root
        # that forgot it silently built with the defaults (U7 review #3).
        providers = BuildProviders(
            llm=factory.llm(), vlm=factory.vlm(), embedding=factory.embedding()
        )
        return cls(
            graph_repo,
            search_repo,
            cache,
            providers=providers,
            ingestion_factory=lambda llm, vlm: IngestionService.from_providers(llm, vlm),  # type: ignore[arg-type]
            topology_factory=lambda wiki: TopologyBuilder(wiki=wiki, tuning=tuning),
            ontology_factory=lambda llm, emb, wiki: OntologyBuilder(
                llm=llm, embedding=emb, wiki=wiki, dedup_threshold=tuning.dedup_threshold
            ),
            wiki_factory=lambda world_id, llm, emb: CommonsenseWiki(
                search_repo, llm, emb, world_id=world_id  # type: ignore[arg-type]
            ),
            distiller_factory=lambda llm: PriorDistiller(llm),  # type: ignore[arg-type]
            linker_factory=lambda llm, emb: WikiPriorLinker(llm, emb),  # type: ignore[arg-type]
            exporter=exporter,
            backup_dir=backup_dir,
        )

    # ------------------------------------------------------------------ #
    def build(self, world_id: str, inputs: WorldInputs, *, replace: bool = True) -> BuildReport:
        """One build per world at a time (U8 review #2): a build takes minutes of LLM work
        before it writes, so a second request for the same world — a reopened panel, a
        retry after a proxy timeout — is refused instead of committing a second copy."""
        with self._building_lock:
            if world_id in self._building:
                raise BuildInProgressError(f"a build of world {world_id!r} is already running")
            self._building.add(world_id)
        try:
            return self._build(world_id, inputs, replace=replace)
        finally:
            with self._building_lock:
                self._building.discard(world_id)

    def _build(self, world_id: str, inputs: WorldInputs, *, replace: bool) -> BuildReport:
        counter = LLMCallCounter()
        llm = counter.wrap_llm(self._providers.llm)
        vlm = counter.wrap_vlm(self._providers.vlm)
        embedding = counter.wrap_embedding(self._providers.embedding)
        warnings: list[BuildWarning] = []

        exists = world_id in self._graph.list_world_ids()
        if exists and not replace:
            raise WorldExistsError(f"world already exists: {world_id}")

        # ---- prepare: nothing below touches the graph ---------------------- #
        ingestion = self._ingestion_factory(llm, vlm).ingest_all(world_id, inputs)
        warnings.extend(ingestion.warnings)
        if not (ingestion.region_hints or ingestion.entities or ingestion.knowledge):
            warnings.append(
                BuildWarning(stage="ingestion", severity="error", message="nothing ingested")
            )
            return self._report(world_id, warnings, counter)

        wiki = self._wiki_factory(world_id, llm, embedding) if self._wiki_factory else None
        topology_builder = self._topology_factory(wiki)
        ontology_builder = self._ontology_factory(llm, embedding, wiki)

        topo_build = topology_builder.build(ingestion, world_id=world_id)
        topology = topo_build.topology
        warnings.extend(topo_build.warnings)
        if not topology.regions:
            warnings.append(
                BuildWarning(stage="topology", severity="error", message="no regions produced")
            )
            return self._report(world_id, warnings, counter)

        priors: list[WikiPrior] = []
        prior_links: list[WikiPriorLink] = []
        if self._distiller_factory is not None:
            priors = self._distiller_factory(llm).distill(ingestion, topology, world_id=world_id)
            if priors and self._linker_factory is not None:
                prior_links = self._linker_factory(llm, embedding).link(priors, world_id=world_id)

        # a replace deletes the old world's priors: connection refs into them would
        # dangle, so keep the rationale text and drop the ref (review U2 #14). Priors this
        # build's wiki made by LLM fallback are stored, so refs to them stay (U3 BR-U3-29).
        topo_created = _created_priors(wiki)
        new_prior_ids = {p.id for p in priors} | {p.id for p in topo_created}
        for c in topology.connections:
            if c.wiki_prior_ref and c.wiki_prior_ref not in new_prior_ids:
                warnings.append(
                    BuildWarning(
                        stage="topology",
                        item_id=c.wiki_prior_ref,
                        message=f"connection {c.source_region_id}->{c.target_region_id}: "
                        "prior ref belonged to the replaced world; ref dropped, rationale kept",
                    )
                )
                c.wiki_prior_ref = None

        # ---- commit: from here on the old world is gone ------------------- #
        replaced = False
        backup_path: Path | None = None
        onto_build: OntologyBuild | None = None
        kg = None
        try:
            if exists:
                backup_path = self._backup(world_id, warnings)
                self._graph.delete_world(world_id)
                replaced = True  # the graph is gone from here on, whatever happens next
                self._cache.invalidate(world_id)
                self._search.delete_world(world_id)
            first_priors = priors + topo_created
            if first_priors:  # persist first so corroboration's single-world wiki can find them
                persist_graph(
                    self._graph,
                    self._search,
                    embedding,
                    world_id,
                    priors=first_priors,
                    prior_links=prior_links,
                    warnings=warnings,
                )
            onto_build = ontology_builder.build(ingestion, topology, world_id=world_id)
            kg = onto_build.kg
            warnings.extend(onto_build.warnings)
            # priors the ontology step made go in before the knowledge whose DERIVED_FROM
            # edges point at them (BLM §5.1)
            topo_ids = {p.id for p in topo_created}
            onto_created = [p for p in _created_priors(wiki) if p.id not in topo_ids]
            if onto_created:
                persist_graph(
                    self._graph,
                    self._search,
                    embedding,
                    world_id,
                    priors=onto_created,
                    warnings=warnings,
                )
            if getattr(wiki, "fallback_capped", False):
                warnings.append(
                    BuildWarning(
                        stage="wiki",
                        message=f"LLM fallback priors capped at {WIKI_FALLBACK_MAX}; later "
                        "lookups kept the computed weight without a prior",
                    )
                )
            persist_graph(
                self._graph,
                self._search,
                embedding,
                world_id,
                regions=topology.regions,
                entities=kg.entities,
                knowledge=kg.knowledge,
                connections=topology.connections,
                scopes=kg.scopes,
                relations=kg.relations,
                meta=WorldMeta(
                    id=world_id,
                    name=getattr(inputs, "name", None) or world_id,
                    description=getattr(inputs, "description", None),
                    last_writer="build",
                ),
                warnings=warnings,
            )
        except Exception as exc:  # the old world may already be gone: report, don't vanish
            logger.exception("commit phase failed for %s", world_id)
            warnings.append(
                BuildWarning(
                    stage="commit",
                    severity="error",
                    message=f"commit failed after {'replacing' if replaced else 'preparing'} "
                    f"the world: {exc}"
                    + (f"; restore from backup {backup_path}" if backup_path else ""),
                )
            )
            report = self._report(world_id, warnings, counter)
            report.replaced = replaced
            report.backup_path = str(backup_path) if backup_path else None
            return report
        finally:
            self._cache.invalidate(world_id)

        assert kg is not None
        corroborations = sum(
            1 for k in kg.knowledge if str(k.provenance.source) == SourceKind.INFERRED.value
        )
        return BuildReport(
            world_id=world_id,
            regions_created=len(topology.regions),
            connections_created=len(topology.connections),
            entities_created=len(kg.entities),
            knowledge_created=len(kg.knowledge),
            corroborations_created=corroborations,
            warnings=warnings,
            unscoped_knowledge_ids=list(kg.unscoped_knowledge_ids),
            llm_calls=counter.llm_calls,
            embedding_calls=counter.embedding_calls,
            replaced=replaced,
            backup_path=str(backup_path) if backup_path else None,
            priors_created=len(priors) + len(_created_priors(wiki)),
        )

    # ------------------------------------------------------------------ #
    def _report(
        self, world_id: str, warnings: list[BuildWarning], counter: LLMCallCounter
    ) -> BuildReport:
        return BuildReport(
            world_id=world_id,
            warnings=warnings,
            llm_calls=counter.llm_calls,
            embedding_calls=counter.embedding_calls,
        )

    def _backup(self, world_id: str, warnings: list[BuildWarning]) -> Path | None:
        """Write the old world to ``backup_dir`` before replacing it (BR-U2-11). Best effort."""
        if self._exporter is None or self._backup_dir is None:
            return None
        try:
            data = self._exporter.export_world(world_id)
            self._backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
            path = self._backup_dir / f"{world_id}-{stamp}-{uuid.uuid4().hex[:6]}.world.json"
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True, default=str),
                encoding="utf-8",
            )
            return path
        except Exception as exc:
            warnings.append(BuildWarning(stage="backup", message=f"backup skipped: {exc}"))
            logger.warning("world backup failed for %s: %s", world_id, exc)
            return None


def _created_priors(wiki) -> list[WikiPrior]:
    """Priors the build's wiki made by LLM fallback (U3 BR-U3-29); a factory may hand
    back a stand-in without them."""
    return list(getattr(wiki, "created_priors", None) or [])
