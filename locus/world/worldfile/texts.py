"""The English texts of a World File that a translation may cover (V3, FD BLM § 5·6).

``(kind, id, field) -> text`` for the world itself, its regions, NPCs, event seeds and
knowledge — the fields of ``TRANSLATABLE_FIELDS``. A blank text is not a translation
target and is left out (BR-V3-04). Pure: the demo check reads it for coverage and the
seeding reads it as "the text now" (BR-V3-20).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from locus.shared.models import fallback_title
from locus.shared.models.i18n import TRANSLATABLE_FIELDS
from locus.world.worldfile.schema import WorldFile

TextKey = tuple[str, str, str]  # (kind, id, field)


def translatable_texts(file: WorldFile) -> dict[TextKey, str]:
    out: dict[TextKey, str] = {}
    sections: list[tuple[str, Iterable[Any]]] = [
        ("world", [file.world]),
        ("region", file.regions),
        ("npc", file.npcs),
        ("event_seed", file.event_seeds),
        ("knowledge", file.knowledge),
    ]
    for kind, items in sections:
        for item in items:
            for field in TRANSLATABLE_FIELDS[kind]:
                text = getattr(item, field, None)
                if kind == "knowledge" and field == "title" and not (text or "").strip():
                    # read back from the graph an empty title is the statement's (BR-A2):
                    # that is the title a screen shows, so it is the one to translate
                    # (code review 01 #12)
                    text = fallback_title(item.statement)
                if isinstance(text, str) and text.strip():
                    out[(kind, item.id, field)] = text
    return out
