"""World editor (U3): one class per responsibility, no facade (domain-entities §2.0).

``EditorWrites`` holds the shared writes; ``Editors`` bundles the classes for the
container and the augmentation Q&A.
"""

from locus.world.editor.bundle import Editors
from locus.world.editor.catalog import WorldCatalog
from locus.world.editor.connections import ConnectionEditor
from locus.world.editor.entities import EntityEditor
from locus.world.editor.knowledge import KnowledgeEditor
from locus.world.editor.models import (
    ConnectionKey,
    ConnectionView,
    EditorRegionView,
    NameRef,
    RegionDeletePlan,
    RegionDeleteReport,
    RegionInUseError,
    ScopedKnowledge,
    WorldSummary,
)
from locus.world.editor.npcs import NpcEditor
from locus.world.editor.regions import RegionEditor
from locus.world.editor.writes import EditorWrites

__all__ = [
    "ConnectionEditor",
    "ConnectionKey",
    "ConnectionView",
    "EditorRegionView",
    "EditorWrites",
    "Editors",
    "EntityEditor",
    "KnowledgeEditor",
    "NameRef",
    "NpcEditor",
    "RegionDeletePlan",
    "RegionDeleteReport",
    "RegionEditor",
    "RegionInUseError",
    "ScopedKnowledge",
    "WorldCatalog",
    "WorldSummary",
]
