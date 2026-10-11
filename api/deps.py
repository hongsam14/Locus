"""FastAPI dependencies: one typed container per boundary (AD-R2).

Routers receive their boundary's container via ``Depends``; a boundary that
failed to assemble (or was not injected) yields 503 for its routes only
(FR-A3). No string lookups on ``app.state``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeVar

from fastapi import Request

from api.errors import ApiError
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


T = TypeVar("T")


def need_service(service: T | None, name: str, code: str = "service_unavailable") -> T:
    """A boundary service that is None without a provider (NFR-4) answers 503 — the one
    rule every router uses (U3 review C7). A service that is None only for want of an
    LLM passes ``code="llm_unavailable"``, which the screens read as "needs a key"
    (BR-U8-27, V2 review #2)."""
    if service is None:
        raise ApiError(503, f"{name} unavailable", code)
    return service


def _containers(request: Request) -> Containers:
    return getattr(request.app.state, "containers", None) or Containers()


def _require(value, name: str):
    if value is None:
        raise ApiError(503, f"{name} boundary unavailable", "service_unavailable")
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


def lang_settings(request: Request) -> Settings:
    """Settings that decide the display language. Without an assembled shared container
    (tests inject only some boundaries) the settings' own defaults apply."""
    shared = _containers(request).shared
    return shared.settings if shared is not None else Settings.model_construct()


def display_lang(request: Request, lang: str | None = None) -> str:
    """The display language of this request (U5, FD-U5 Q1=A, BR-U5-15).

    ``?lang=`` overrides the server default (``TRANSLATION_TARGET_LANG``) and must be
    one of ``SUPPORTED_LANGS`` — validated once here at the edge, so an unsupported
    value can never become a translation-cache key (400). Without an assembled shared
    container (tests inject only some boundaries) the settings' own defaults apply.
    """
    settings = lang_settings(request)
    chosen = (lang or settings.translation_target_lang).strip().lower()
    if chosen not in settings.supported_langs:
        raise ApiError(400, f"unsupported lang: {chosen}", "unsupported_lang")
    return chosen
