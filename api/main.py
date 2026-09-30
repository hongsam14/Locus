"""FastAPI application factory — composes the five boundaries (AD-R2, FR-A3).

Each boundary is assembled by its own ``assemble_*`` and handed to its routers
through a typed container. A boundary that fails to assemble is left ``None``
and only its routes answer 503; the others keep working.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.deps import Containers, lang_settings
from api.routers import gm as gm_router
from api.routers import knowledge as knowledge_router
from api.routers import play as play_router
from api.routers import world as world_router
from locus.knowledge.wiring import KnowledgeContainer
from locus.localization.wiring import LocalizationContainer
from locus.play.wiring import PlayContainer
from locus.shared.wiring import SharedContainer
from locus.world.wiring import WorldContainer

logger = logging.getLogger(__name__)


def assemble_all(containers: Containers) -> Containers:  # pragma: no cover - live services
    """Fill in every container that was not injected. Failures isolate per boundary."""
    from locus.knowledge.wiring import assemble_knowledge
    from locus.localization.storage.schema import ensure_localization_schema
    from locus.localization.wiring import assemble_localization
    from locus.play.storage.schema import ensure_play_schema
    from locus.play.wiring import assemble_play
    from locus.shared.storage.schema import ensure_world_schema
    from locus.shared.wiring import assemble_shared
    from locus.world.wiring import assemble_world

    if containers.shared is None:
        containers.shared = assemble_shared(strict=False)
        containers.owned.add("shared")
    shared = containers.shared

    def _try(name: str, fn):
        try:
            return fn()
        except Exception:
            logger.exception("%s boundary unavailable", name)
            return None

    if shared.graph is not None and shared.search is not None:
        _try("world schema", lambda: ensure_world_schema(shared.graph, shared.search))
    if shared.sql_engine is not None:
        _try("play schema", lambda: ensure_play_schema(shared.sql_engine))
        _try("localization schema", lambda: ensure_localization_schema(shared.sql_engine))

    if containers.knowledge is None:
        containers.knowledge = _try("knowledge", lambda: assemble_knowledge(shared))
    if containers.world is None and containers.knowledge is not None:
        containers.world = _try("world", lambda: assemble_world(shared, containers.knowledge))
    if containers.play is None and containers.knowledge is not None:
        containers.play = _try("play", lambda: assemble_play(shared, containers.knowledge))
        if containers.play is not None:
            containers.owned.add("play")  # only an owned executor may be shut down
    if containers.localization is None:
        containers.localization = _try("localization", lambda: assemble_localization(shared))
        if containers.localization is not None:
            containers.owned.add("localization")
    return containers


def create_app(
    *,
    shared: SharedContainer | None = None,
    knowledge: KnowledgeContainer | None = None,
    world: WorldContainer | None = None,
    play: PlayContainer | None = None,
    localization: LocalizationContainer | None = None,
    assemble_missing: bool | None = None,
) -> FastAPI:
    """Build the app.

    Tests inject the containers they need (the rest answer 503). With no
    container injected, everything is assembled from settings on startup;
    ``assemble_missing=True`` forces assembly of the missing ones even when some
    were injected.
    """
    containers = Containers(
        shared=shared, knowledge=knowledge, world=world, play=play, localization=localization
    )
    injected = any(c is not None for c in (shared, knowledge, world, play, localization))
    do_assemble = (not injected) if assemble_missing is None else assemble_missing

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if do_assemble:
            assemble_all(containers)
        app.state.containers = containers
        if containers.play is not None:  # U4 BR-U4-15: runs interrupted by a restart
            try:
                stale = containers.play.repo.fail_stale_runs(reason="interrupted")
                if stale:
                    logger.warning("marked %d interrupted turn run(s) failed", stale)
            except Exception:  # pragma: no cover - storage down: play routes will tell
                logger.exception("could not clean up stale turn runs")
        try:
            yield
        finally:
            # Only an owned play container's executor is shut down: shutting down an
            # injected one is one-way and left its owner's later requests failing
            # (code review U4-2 #14).
            if "play" in containers.owned and containers.play is not None:
                timeout = (
                    containers.shared.settings.turn_shutdown_timeout_s
                    if containers.shared is not None
                    else 30.0
                )
                try:
                    containers.play.executor.shutdown(timeout)
                except Exception:  # pragma: no cover
                    logger.exception("turn executor shutdown failed")
            # close only what assemble_all created; injected containers stay
            # usable for their owner (review U1 #13)
            if "localization" in containers.owned and containers.localization is not None:
                containers.localization.close()
            if "shared" in containers.owned and containers.shared is not None:
                containers.shared.close()

    app = FastAPI(title="Locus", version="0.2.0", lifespan=lifespan)
    app.state.containers = containers

    @app.get("/health", tags=["health"])
    def health() -> JSONResponse:
        """``ok`` = every boundary up, ``degraded`` = some down, 503 = none up (review U1 #4)."""
        c: Containers = app.state.containers
        boundaries = {
            name: getattr(c, name) is not None
            for name in ("world", "knowledge", "play", "localization")
        }
        if not any(boundaries.values()):
            return JSONResponse(
                status_code=503, content={"status": "unavailable", "boundaries": boundaries}
            )
        status = "ok" if all(boundaries.values()) or not do_assemble else "degraded"
        return JSONResponse(content={"status": status, "boundaries": boundaries})

    @app.get("/api/langs", tags=["meta"])
    def langs(request: Request) -> dict[str, object]:
        """The display languages this server accepts (review U5 #2). The web client sends
        ``?lang=`` only for one of these, so a server configured for English only never
        receives ``?lang=ko`` and answers 400 to every read."""
        settings = lang_settings(request)
        return {
            "default": settings.translation_target_lang,
            "supported": list(settings.supported_langs),
        }

    app.include_router(world_router.router)
    app.include_router(knowledge_router.router)
    app.include_router(play_router.router)
    app.include_router(gm_router.router)
    return app


# Module-level app for `uvicorn api.main:app`.
app = create_app()
