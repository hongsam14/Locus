"""World File v1 — the save format (U2 W9, FR-B8, BR-U2-1/2).

A superset of the pre-U2 export JSON: every canonical section as plain model dumps,
plus ``format_version`` and a ``world`` block. ``WorldFile.parse`` is the single
entry point: it accepts v1, reads a legacy export (no ``format_version``) as v0
with ``world.id`` taken from its top-level ``world_id``, ignores unknown keys at
every level, and turns any validation failure into ``UnsupportedWorldFile``.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from locus.shared.models import (
    NPC,
    ConnectionEdge,
    Entity,
    Knowledge,
    Provenance,
    Region,
    Relation,
    ScopeLink,
    WikiPrior,
    WikiPriorLink,
)

FORMAT_VERSION = 1
SUPPORTED_VERSIONS: tuple[int, ...] = (FORMAT_VERSION,)
# Fixed namespace for deterministic id remapping (BR-U2-4). Never change it.
NAMESPACE_LOCUS = uuid.UUID("5d0f3a3e-2c7b-4f1e-9a8c-7b6d5e4f3a21")

SECTIONS: dict[str, type[BaseModel]] = {
    "regions": Region,
    "connections": ConnectionEdge,
    "entities": Entity,
    "relations": Relation,
    "knowledge": Knowledge,
    "scopes": ScopeLink,
    "priors": WikiPrior,
    "prior_links": WikiPriorLink,
    "npcs": NPC,
}
LEGACY_SECTIONS = ("regions", "connections", "entities", "knowledge", "scopes")


class UnsupportedWorldFile(ValueError):
    """Not a World File, an unsupported ``format_version``, or invalid content (HTTP 422)."""


class WorldFileMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    description: str | None = None


class WorldFile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    format_version: int
    world: WorldFileMeta
    exported_at: datetime | None = None
    regions: list[Region] = Field(default_factory=list)
    connections: list[ConnectionEdge] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    knowledge: list[Knowledge] = Field(default_factory=list)
    scopes: list[ScopeLink] = Field(default_factory=list)
    priors: list[WikiPrior] = Field(default_factory=list)
    prior_links: list[WikiPriorLink] = Field(default_factory=list)
    npcs: list[NPC] = Field(default_factory=list)

    # -- parsing ---------------------------------------------------------- #
    @classmethod
    def parse(cls, raw: Any) -> WorldFile:
        if not isinstance(raw, dict):
            raise UnsupportedWorldFile("not a world file: expected a JSON object")
        if "format_version" not in raw:
            return cls._parse_legacy(raw)
        version = raw.get("format_version")
        if version not in SUPPORTED_VERSIONS:
            raise UnsupportedWorldFile(
                f"unsupported format_version {version!r}; supported: {list(SUPPORTED_VERSIONS)}"
            )
        data = {k: v for k, v in raw.items() if k in cls.model_fields}
        for name, model in SECTIONS.items():
            data[name] = [_strip(model, item) for item in _section(raw, name)]
        try:
            return cls.model_validate(data)
        except ValidationError as exc:
            raise UnsupportedWorldFile(f"invalid world file: {exc}") from exc

    @classmethod
    def _parse_legacy(cls, raw: dict) -> WorldFile:
        """Pre-U2 export JSON: top-level ``world_id`` names the source world (BR-U2-1)."""
        world_id = raw.get("world_id")
        if not isinstance(world_id, str) or not world_id:
            raise UnsupportedWorldFile("not a world file: no format_version and no world_id")
        data: dict[str, Any] = {
            "format_version": 0,
            "world": {"id": world_id, "name": world_id},
        }
        for name in LEGACY_SECTIONS:
            data[name] = [_strip(SECTIONS[name], item) for item in _section(raw, name)]
        try:
            return cls.model_validate(data)
        except ValidationError as exc:
            raise UnsupportedWorldFile(f"invalid legacy export: {exc}") from exc

    # -- helpers ---------------------------------------------------------- #
    def counts(self) -> dict[str, int]:
        return {name: len(getattr(self, name)) for name in SECTIONS}

    def to_json(self) -> str:
        """Deterministic text: sorted keys, 2-space indent (BR-U2-3)."""
        return json.dumps(
            self.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True
        )


def _section(raw: dict, name: str) -> list:
    value = raw.get(name, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise UnsupportedWorldFile(f"invalid world file: section {name!r} must be a list")
    return value


def _strip(model: type[BaseModel], item: Any) -> Any:
    """Drop unknown keys of a section item (and its ``provenance``) so a newer file
    still loads (BR-U2-2); anything else is left for validation to judge."""
    if not isinstance(item, dict):
        return item
    out = {k: v for k, v in item.items() if k in model.model_fields}
    prov = out.get("provenance")
    if isinstance(prov, dict):
        out["provenance"] = {k: v for k, v in prov.items() if k in Provenance.model_fields}
    pos = out.get("position")
    if isinstance(pos, dict):
        out["position"] = {k: v for k, v in pos.items() if k in ("x", "y")}
    return out
