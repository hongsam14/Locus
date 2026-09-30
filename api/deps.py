"""FastAPI dependencies: one typed container per boundary (AD-R2).

Routers receive their boundary's container via ``Depends``; a boundary that
failed to assemble (or was not injected) yields 503 for its routes only
(FR-A3). No string lookups on ``app.state``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import HTTPException, Request

from locus.knowledge.wiring import KnowledgeContainer
from locus.localization.wiring import LocalizationContainer
from locus.play.wiring import PlayContainer
from locus.shared.config import Settings
from locus.shared.wiring import SharedContainer
from locus.world.wiring import WorldContainer


@dataclass
class Containers:
    shared: SharedContainer | None = None
    knowledge: KnowledgeContainer | None = None
    world: WorldContainer | None = None
    play: PlayContainer | None = None
    localization: LocalizationContainer | None = None
    # names of containers assemble_all created (and therefore closes); injected ones are not
    owned: set[str] = field(default_factory=set)


def _containers(request: Request) -> Containers:
    return getattr(request.app.state, "containers", None) or Containers()


def _require(value, name: str):
    if value is None:
        raise HTTPException(status_code=503, detail=f"{name} boundary unavailable")
    return value


def get_shared(request: Request) -> SharedContainer:
    return _require(_containers(request).shared, "shared")


def get_knowledge(request: Request) -> KnowledgeContainer:
    return _require(_containers(request).knowledge, "knowledge")


def get_world(request: Request) -> WorldContainer:
    return _require(_containers(request).world, "world")


def get_play(request: Request) -> PlayContainer:
    return _require(_containers(request).play, "play")


def get_localization(request: Request) -> LocalizationContainer | None:
    """Optional: ``None`` when translation is disabled or unavailable (originals shown)."""
    return _containers(request).localization


def get_play_optional(request: Request) -> PlayContainer | None:
    """Optional play boundary: world routes ask it about open sessions before a replace
    (NFR-9) and skip the check when play is not assembled."""
    return _containers(request).play


def display_lang(request: Request, lang: str | None = None) -> str:
    """The display language of this request (U5, FD-U5 Q1=A, BR-U5-15).

    ``?lang=`` overrides the server default (``TRANSLATION_TARGET_LANG``) and must be
    one of ``SUPPORTED_LANGS`` — validated once here at the edge, so an unsupported
    value can never become a translation-cache key (400). Without an assembled shared
    container (tests inject only some boundaries) the settings' own defaults apply.
    """
    shared = _containers(request).shared
    settings = shared.settings if shared is not None else Settings.model_construct()
    chosen = (lang or settings.translation_target_lang).strip().lower()
    if chosen not in settings.supported_langs:
        raise HTTPException(status_code=400, detail=f"unsupported lang: {chosen}")
    return chosen
