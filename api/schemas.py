"""API request/response DTOs.

Display-only fields (``*_ko``) live here, never on domain models (FR-A2/G2):
routers ask the localization boundary for a mapping and copy it into these
response types with :func:`localize`.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any, TypeVar

from pydantic import BaseModel, Field

from locus.localization.service import Enrichment
from locus.localization.wiring import LocalizationContainer
from locus.play.models import (
    Conversation,
    Deed,
    DeedAppraisal,
    DeedView,
    EventCategory,
    EventLifecycle,
    GameSession,
    NpcReply,
    Player,
    RegionView,
    SessionEvent,
    SessionRumor,
    WorldState,
)
from locus.shared.models import NPC, KnowledgeView, QueryResult

# --- requests ---------------------------------------------------------------- #


class SupportUpdate(BaseModel):
    support: float = Field(allow_inf_nan=False)  # NaN would clamp to 1.0 (U7 review §3)


class DistortionUpdate(BaseModel):
    degree: float = Field(allow_inf_nan=False)


class EventCreate(BaseModel):
    region_id: str
    category: EventCategory
    description: str = ""
    magnitude: float = Field(allow_inf_nan=False)
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


class UnignoreIn(BaseModel):
    """``POST /augmentation/runs/{id}/unignore`` body (U3, FD 검토 R-08)."""

    issue_key: str


class LocalizedKnowledgeView(KnowledgeView):
    statement_ko: str | None = None
    title_ko: str | None = None


class QueryResultOut(QueryResult):
    items: list[LocalizedKnowledgeView] = []  # type: ignore[assignment]


class RumorOut(SessionRumor):
    statement_ko: str | None = None


class EventOut(SessionEvent):
    description_ko: str | None = None


# --- U5 NPC dialogue ----------------------------------------------------------- #
class SayIn(BaseModel):
    """The player's line. Length and emptiness are checked by the service (400)."""

    text: str


class NpcSummaryOut(BaseModel):
    """An NPC of the player's region, and whether a conversation already exists."""

    npc: NPC
    has_conversation: bool
    message_count: int


# Dialogue is generated in the display language and never translated (A-1), so the
# domain models are the response models as they are.
ConversationOut = Conversation
NpcReplyOut = NpcReply


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

# The language every stored, embedded and searched text is written in (C-1, FR-G2).
SOURCE_LANG = "en"


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
    lang: str | None = None,
) -> Enrichment:
    """Cache-only translation mapping; ``{}`` when localization is off.

    ``lang`` is the display language (``None`` = the server default). When it is the
    language the source text is stored in (English, C-1) there is nothing to translate
    and no warm is scheduled — otherwise ``?lang=en`` would warm en→en rows (BR-U5-19).
    """
    if loc is None or loc.translations is None or not items:
        return {}
    target = (lang or loc.translations.default_lang).lower()
    if target == SOURCE_LANG:
        return {}
    return loc.translations.enrich(
        items,
        kind=kind,
        fields=fields,
        id_attr=id_attr,
        world_id=world_id,
        session_id=session_id,
        lang=target,
    )


def localize_query_result(
    result: QueryResult,
    loc: LocalizationContainer | None,
    *,
    session_id: str | None = None,
    lang: str | None = None,
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
            lang=lang,
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
            lang=lang,
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
    view: RegionView,
    loc: LocalizationContainer | None,
    *,
    world_id: str,
    session_id: str,
    lang: str | None = None,
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
            lang=lang,
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
        loc, view.rumors, kind="rumor", fields=["statement"], session_id=session_id, lang=lang
    )
    rumors = localize(view.rumors, RumorOut, rumor_enrichment, [("statement", "statement_ko")])
    data: dict[str, Any] = view.model_dump()
    data.update(facts=facts, hearsay=hearsay, rumors=rumors)
    return RegionViewOut(**data)


_log = logging.getLogger(__name__)


def purge_translations(
    loc: LocalizationContainer | None,
    *,
    kind: str | None = None,
    ids: list[str] | None = None,
    world_id: str | None = None,
    session_id: str | None = None,
) -> int:
    """Drop cached translations whose source is gone (U5 Q4=A, BR-U5-23).

    Called by the composition root only (play and world never import localization).
    A side job: without localization it does nothing, and a failure is logged and
    never breaks the response it rides on.
    """
    if loc is None or loc.translations is None:
        return 0
    if ids is not None and not ids:
        return 0
    try:
        return loc.translations.purge(kind=kind, ids=ids, world_id=world_id, session_id=session_id)
    except Exception:
        _log.exception("translation purge failed (kind=%s, world=%s)", kind, world_id)
        return 0


# --- U6 deeds (GM view) ---------------------------------------------------------- #
class DeedOut(Deed):
    text_ko: str | None = None
    region_name: str = ""
    witness_names: list[str] = []


class DeedAppraisalOut(DeedAppraisal):
    retelling_ko: str | None = None
    npc_name: str = ""


class DeedViewOut(BaseModel):
    """A deed for the GM panel: names filled from the snapshot (an id when the region or
    the NPC was edited away), translations from the cache (BR-U6-33)."""

    deed: DeedOut
    appraisals: list[DeedAppraisalOut]
    rumors: list[RumorOut]
    reached_region_ids: list[str]
    reached_region_names: list[str]


def localize_deed_views(
    loc: Any,
    views: list[DeedView],
    *,
    regions: dict[str, str],
    npcs: dict[str, str],
    rumors_out: dict[str, Any],
    session_id: str,
    lang: str,
) -> list[DeedViewOut]:
    """The GM deed panel's rows with names and ``*_ko`` fields (U6 review C12: the
    translation lookup lives with the other localizers, not in the router)."""
    deeds = [v.deed for v in views]
    told = [a for v in views for a in v.appraisals if a.retelling]
    deed_tr = enrichment_for(
        loc, deeds, kind="deed", fields=["text"], session_id=session_id, lang=lang
    )
    told_tr = enrichment_for(
        loc, told, kind="deed_appraisal", fields=["retelling"], session_id=session_id, lang=lang
    )
    out: list[DeedViewOut] = []
    for v in views:
        deed = DeedOut(
            **v.deed.model_dump(),
            text_ko=deed_tr.get(v.deed.id, {}).get("text"),
            region_name=regions.get(v.deed.region_id, v.deed.region_id),
            witness_names=[npcs.get(n, n) for n in v.deed.witnessed_npc_ids],
        )
        judged = [
            DeedAppraisalOut(
                **a.model_dump(),
                retelling_ko=told_tr.get(a.id, {}).get("retelling"),
                npc_name=npcs.get(a.npc_id, a.npc_id),
            )
            for a in v.appraisals
        ]
        out.append(
            DeedViewOut(
                deed=deed,
                appraisals=judged,
                rumors=[rumors_out[r.id] for r in v.rumors],
                reached_region_ids=v.reached_region_ids,
                reached_region_names=[regions.get(r, r) for r in v.reached_region_ids],
            )
        )
    return out


# U7: the GM overlay carries names already and no translated field (FR-D4).
WorldStateOut = WorldState


# --------------------------------------------------------------------------- #
# U3 world editor (BLM §7). Knowledge carries ``*_ko``; NPC text is shown as written
# (no ``npc`` translation kind, BR-U3-37).
# --------------------------------------------------------------------------- #
from locus.shared.models import ConnectionEdge, ConnectionKind, Knowledge, Region  # noqa: E402
from locus.world.demo import DemoInfo  # noqa: E402
from locus.world.editor import (  # noqa: E402
    ConnectionView,
    EditorRegionView,
    NameRef,
    ScopedKnowledge,
)
from locus.world.wiki.schemas import BrokenRef, PriorUsage  # noqa: E402


class LocalizedKnowledge(Knowledge):
    statement_ko: str | None = None
    title_ko: str | None = None


class ScopedKnowledgeOut(ScopedKnowledge):
    knowledge: LocalizedKnowledge


class EditorRegionViewOut(BaseModel):
    """``EditorRegionView`` with translated knowledge (same fields)."""

    region: Region
    children: list[NameRef] = Field(default_factory=list)
    connections: list[ConnectionView] = Field(default_factory=list)
    knowledge: list[ScopedKnowledgeOut] = Field(default_factory=list)
    npcs: list[NPC] = Field(default_factory=list)


class ConnectionSave(ConnectionEdge):
    """``PUT …/connections``: a pair to save; ``previous_kind`` makes it a kind change
    that keeps weight, rationale, prior ref and provenance (BR-U3-11)."""

    previous_kind: ConnectionKind | None = None


class ScopesIn(BaseModel):
    region_ids: list[str] = Field(default_factory=list)


class PriorRefsOut(BaseModel):
    usages: list[PriorUsage] = Field(default_factory=list)
    broken: list[BrokenRef] = Field(default_factory=list)


def localize_knowledge(
    items: Sequence[Knowledge],
    loc: LocalizationContainer | None,
    *,
    world_id: str,
    lang: str | None = None,
) -> list[LocalizedKnowledge]:
    enrichment = enrichment_for(
        loc, items, kind="knowledge", fields=["statement", "title"], world_id=world_id, lang=lang
    )
    return localize(
        items,
        LocalizedKnowledge,
        enrichment,
        [("statement", "statement_ko"), ("title", "title_ko")],
    )


def localize_editor_view(
    view: EditorRegionView, loc: LocalizationContainer | None, *, lang: str | None = None
) -> EditorRegionViewOut:
    knowledge = localize_knowledge(
        [s.knowledge for s in view.knowledge], loc, world_id=view.region.world_id, lang=lang
    )
    data = view.model_dump(exclude={"knowledge"})
    return EditorRegionViewOut(
        **data,
        knowledge=[
            ScopedKnowledgeOut(knowledge=k, scope_region_ids=s.scope_region_ids)
            for k, s in zip(knowledge, view.knowledge, strict=True)
        ],
    )


class DemoInfoOut(BaseModel):
    """``GET /api/world/demos``: a manifest entry as the home screen needs it (U8 FD
    domain-entities §1). File and source paths stay on the server."""

    name: str
    title: str
    description: str | None = None
    credits: str | None = None
    start_region_id: str
    has_sources: bool = False

    @classmethod
    def of(cls, info: DemoInfo) -> DemoInfoOut:
        return cls(
            name=info.name,
            title=info.title,
            description=info.description,
            credits=info.credits,
            start_region_id=info.start_region_id,
            has_sources=info.has_sources,
        )
