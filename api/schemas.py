"""API request/response DTOs.

Display-only fields (``*_ko``) live here, never on domain models (FR-A2/G2):
routers ask the localization boundary for a mapping and copy it into these
response types with :func:`localize`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypeVar

from pydantic import BaseModel

from locus.localization.service import Enrichment
from locus.localization.wiring import LocalizationContainer
from locus.play.models import (
    EventCategory,
    EventLifecycle,
    GameSession,
    Player,
    RegionView,
    SessionEvent,
    SessionRumor,
)
from locus.shared.models import KnowledgeView, QueryResult

# --- requests ---------------------------------------------------------------- #


class SupportUpdate(BaseModel):
    support: float


class DistortionUpdate(BaseModel):
    degree: float


class EventCreate(BaseModel):
    region_id: str
    category: EventCategory
    description: str = ""
    magnitude: float
    lifecycle: EventLifecycle | None = None


# --- responses --------------------------------------------------------------- #


class WorldInfo(BaseModel):
    """One row of the world list (US-6.4 backend, BR-U2-24)."""

    id: str
    name: str
    description: str | None = None
    region_count: int = 0
    updated_at: str | None = None
    last_writer: str | None = None
    open_sessions: int | None = None  # None when the play boundary is not assembled


class LocalizedKnowledgeView(KnowledgeView):
    statement_ko: str | None = None
    title_ko: str | None = None


class QueryResultOut(QueryResult):
    items: list[LocalizedKnowledgeView] = []  # type: ignore[assignment]


class RumorOut(SessionRumor):
    statement_ko: str | None = None


class EventOut(SessionEvent):
    description_ko: str | None = None


# --- U4 player mode ------------------------------------------------------------ #
class SessionStartOut(BaseModel):
    """Response of a player-mode session start (201): the session and its player."""

    session: GameSession
    player: Player


class RegionViewOut(RegionView):
    """RegionView with display translations (``*_ko``) for the player screen.

    The region *name* is not translated yet: no ``kind="region"`` translation exists,
    so the field it used to carry was always ``None`` (code review U4 #7). Region-name
    translation belongs to the language unit (U5).
    """

    facts: list[LocalizedKnowledgeView] = []  # type: ignore[assignment]
    hearsay: list[LocalizedKnowledgeView] = []  # type: ignore[assignment]
    rumors: list[RumorOut] = []  # type: ignore[assignment]


T = TypeVar("T", bound=BaseModel)


def localize(
    items: Sequence[BaseModel],
    out_cls: type[T],
    enrichment: Enrichment,
    fields: Sequence[tuple[str, str]],
    *,
    id_attr: str = "id",
) -> list[T]:
    """Copy each item into ``out_cls`` and fill ``dst`` from ``enrichment[id][src]``."""
    out: list[T] = []
    for it in items:
        data: dict[str, Any] = it.model_dump()
        tr = enrichment.get(str(getattr(it, id_attr)), {})
        for src, dst in fields:
            data[dst] = tr.get(src)
        out.append(out_cls(**data))
    return out


def enrichment_for(
    loc: LocalizationContainer | None,
    items: Sequence[BaseModel],
    *,
    kind: str,
    fields: Sequence[str],
    id_attr: str = "id",
    world_id: str | None = None,
    session_id: str | None = None,
) -> Enrichment:
    """Cache-only translation mapping; ``{}`` when localization is off."""
    if loc is None or loc.translations is None or not items:
        return {}
    return loc.translations.enrich(
        items, kind=kind, fields=fields, id_attr=id_attr, world_id=world_id, session_id=session_id
    )


def localize_query_result(
    result: QueryResult, loc: LocalizationContainer | None, *, session_id: str | None = None
) -> QueryResultOut:
    """Localize a region-knowledge result: canonical items per world, rumor views per session."""
    from locus.play.region_knowledge import is_rumor_view

    rumor_items = [v for v in result.items if is_rumor_view(v)]
    canon_items = [v for v in result.items if not is_rumor_view(v)]
    enrichment: Enrichment = {}
    enrichment.update(
        enrichment_for(
            loc,
            canon_items,
            kind="knowledge",
            fields=["statement", "title"],
            id_attr="knowledge_id",
            world_id=result.world_id,
        )
    )
    enrichment.update(
        enrichment_for(
            loc,
            rumor_items,
            kind="rumor",
            fields=["statement"],
            id_attr="knowledge_id",
            session_id=session_id,
        )
    )
    items = localize(
        result.items,
        LocalizedKnowledgeView,
        enrichment,
        [("statement", "statement_ko"), ("title", "title_ko")],
        id_attr="knowledge_id",
    )
    return QueryResultOut(
        world_id=result.world_id,
        region_id=result.region_id,
        items=items,
        shared_ids=result.shared_ids,
        unique_ids=result.unique_ids,
    )


def localize_region_view(
    view: RegionView, loc: LocalizationContainer | None, *, world_id: str, session_id: str
) -> RegionViewOut:
    """Localize the player screen: canonical facts/hearsay per world, rumors per session."""
    canon_items = list(view.facts) + list(view.hearsay)
    enrichment: Enrichment = {}
    enrichment.update(
        enrichment_for(
            loc,
            canon_items,
            kind="knowledge",
            fields=["statement", "title"],
            id_attr="knowledge_id",
            world_id=world_id,
        )
    )
    facts = localize(
        view.facts,
        LocalizedKnowledgeView,
        enrichment,
        [("statement", "statement_ko"), ("title", "title_ko")],
        id_attr="knowledge_id",
    )
    hearsay = localize(
        view.hearsay,
        LocalizedKnowledgeView,
        enrichment,
        [("statement", "statement_ko"), ("title", "title_ko")],
        id_attr="knowledge_id",
    )
    rumor_enrichment = enrichment_for(
        loc, view.rumors, kind="rumor", fields=["statement"], session_id=session_id
    )
    rumors = localize(view.rumors, RumorOut, rumor_enrichment, [("statement", "statement_ko")])
    data: dict[str, Any] = view.model_dump()
    data.update(facts=facts, hearsay=hearsay, rumors=rumors)
    return RegionViewOut(**data)
