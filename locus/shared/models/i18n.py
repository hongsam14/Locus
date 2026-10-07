"""Display translations of world text (V3, FR-L3, FD domain-entities § 1·2).

``world`` reads a demo's translation file and ``localization`` puts its entries in the
translation cache; the two boundaries never import each other, so the shapes they share
live here (component-dependency.md). A translation is used only while the hash of its
English source equals the hash of the text the world holds now (BR-V3-01): a file entry
carries the source itself (Q2=A) and the hash is computed from it.
"""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from pydantic import Field, ValidationError, model_validator

from locus.shared.models.graph import LocusModel

TranslationKind = Literal["world", "region", "npc", "event_seed", "knowledge"]

# The fields of each kind that a screen shows and a translation may cover (FD § 1). The
# order is the order a translation file lists them in.
TRANSLATABLE_FIELDS: dict[str, tuple[str, ...]] = {
    "world": ("name", "description"),
    "region": ("name", "description"),
    "npc": ("name", "role", "description"),
    "event_seed": ("title", "description"),
    "knowledge": ("statement", "title"),
}

TRANSLATION_FORMAT: Literal["locus.translations"] = "locus.translations"
TRANSLATION_VERSION: Literal[1] = 1


def source_hash(text: str) -> str:
    """Stable hash of a source text, whitespace at the ends ignored (BR-X1-6)."""
    normalized = (text or "").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class TranslationEntry(LocusModel):
    """One line of a translation file: ``text`` translates ``source``, the current
    English text of ``kind``/``id``/``field``."""

    kind: TranslationKind
    id: str = Field(min_length=1)
    field: str
    source: str
    text: str

    @model_validator(mode="after")
    def _known_field_and_text(self) -> TranslationEntry:
        if self.field not in TRANSLATABLE_FIELDS[self.kind]:
            raise ValueError(f"{self.kind} has no translatable field {self.field!r}")
        if not self.source.strip():
            raise ValueError(f"{self.kind} {self.id}.{self.field}: empty source")
        if not self.text.strip():
            raise ValueError(f"{self.kind} {self.id}.{self.field}: empty translation")
        return self

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.kind, self.id, self.field)

    @property
    def source_hash(self) -> str:
        return source_hash(self.source)


class TranslationFile(LocusModel):
    """A demo's translation file for one language (FD domain-entities § 3)."""

    format: Literal["locus.translations"] = TRANSLATION_FORMAT
    version: Literal[1] = TRANSLATION_VERSION
    lang: str = Field(pattern=r"^[a-z]{2}$")
    world_id: str = Field(min_length=1)  # the world.id of the World File it translates
    entries: list[TranslationEntry] = Field(default_factory=list)

    @classmethod
    def parse(cls, data: object) -> TranslationFile:
        """Read a decoded JSON document; ``ValueError`` says what is wrong with it."""
        if not isinstance(data, dict):
            raise ValueError("a translation file is a JSON object")
        if data.get("format") != TRANSLATION_FORMAT:
            raise ValueError(f"not a translation file (format {data.get('format')!r})")
        if data.get("version") != TRANSLATION_VERSION:
            raise ValueError(f"unsupported translation file version {data.get('version')!r}")
        try:
            return cls.model_validate(data)
        except ValidationError as exc:
            first = exc.errors()[0]
            where = ".".join(str(p) for p in first["loc"])
            raise ValueError(
                f"invalid translation file: {exc.error_count()} error(s), first at {where}: "
                f"{first['msg']}"
            ) from exc

    def to_json(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
