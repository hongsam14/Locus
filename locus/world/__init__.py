"""world — build, edit, save/load and enrich a canonical world.

Ingestion -> topology -> (wiki priors) -> ontology -> persistence, plus the
editor, augmentation Q&A, World File export and the bundled demo world.
Depends on ``knowledge`` (read) and ``shared``; never on ``play`` (FR-A2).

In-progress modules (kept, not finished — FR-I): ``ingestion/concept_art_ingestor``,
``wiki/cross_world``, ``augmentation/graph``.
"""

from locus.world.build import WorldBuilder
from locus.world.demo import DemoInfo, DemoSources, DemoWorlds, check_packaged
from locus.world.editor import (
    ConnectionEditor,
    Editors,
    EntityEditor,
    KnowledgeEditor,
    NpcEditor,
    RegionEditor,
    WorldCatalog,
)
from locus.world.wiring import WorldContainer, assemble_world
from locus.world.worldfile.export import WorldFileExporter

__all__ = [
    "WorldBuilder",
    "ConnectionEditor",
    "Editors",
    "EntityEditor",
    "KnowledgeEditor",
    "NpcEditor",
    "RegionEditor",
    "WorldCatalog",
    "WorldFileExporter",
    "DemoInfo",
    "DemoWorlds",
    "DemoSources",
    "check_packaged",
    "WorldContainer",
    "assemble_world",
]
