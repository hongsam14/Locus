"""world router — build / World File / demo / list / edit / wiki / augmentation (editor screen).

No auth (MVP). Replacing a world that has open sessions needs ``confirm=true``; the
router asks the play boundary (when assembled), closes those sessions and reports
their ids (NFR-9, BR-U2-25). LLM-dependent services answer 503 when no provider is
configured (NFR-4).
"""

from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any, TypeVar
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Response, UploadFile

from api.deps import get_localization, get_play_optional, get_shared, get_world
from api.errors import http_error
from api.schemas import UnignoreIn, WorldInfo, purge_translations
from locus.localization.wiring import LocalizationContainer
from locus.play.errors import TurnInProgressError
from locus.play.wiring import PlayContainer
from locus.shared.models import (
    BuildReport,
    GraphSummary,
    ImportReport,
    Knowledge,
    Region,
    WikiPrior,
)
from locus.shared.models.reports import BuildWarning
from locus.shared.wiring import SharedContainer
from locus.world.augmentation.types import (
    AnswerResult,
    AugmentationAnswer,
    AugmentationConflict,
    AugmentationRun,
)
from locus.world.build import WorldExistsError
from locus.world.demo import DemoInfo
from locus.world.ingestion.service import WorldInputs
from locus.world.wiring import WorldContainer
from locus.world.worldfile import UnsupportedWorldFile, WorldFile, to_json_bytes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/world", tags=["world"])

T = TypeVar("T")


def _need(service: T | None, name: str) -> T:
    """LLM-dependent services are None without a provider (NFR-4): their routes 503."""
    if service is None:
        raise HTTPException(status_code=503, detail=f"{name} unavailable")
    return service


def _open_sessions(world_id: str, confirm: bool, play: PlayContainer | None) -> list[str]:
    """Open sessions block a replace unless confirmed (BR-U2-25). Returns the ids that
    will be closed once the replace has actually happened; nothing is closed here, so a
    build/import that fails or never replaces leaves the sessions untouched (review #6).
    Without a play boundary nothing is checked."""
    if play is None:
        return []
    open_ids = [s.id for s in play.sessions.list_sessions(world_id) if str(s.status) == "open"]
    # Pre-flight the turn guard: a session mid-turn cannot be closed, so admitting it
    # here let the destructive replace run and then fail on the close, after the world
    # was already gone (code review U4-2 #3, re-framed root cause).
    busy = [sid for sid in open_ids if play.guard.is_running(sid)]
    if busy:
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"world {world_id!r} has {len(busy)} session(s) mid-turn; "
                "retry once their turns finish",
                "busy_sessions": len(busy),
                "session_ids": busy,
            },
        )
    if open_ids and not confirm:
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"world {world_id!r} has {len(open_ids)} open session(s); "
                "pass confirm=true to close them and replace the world",
                "open_sessions": len(open_ids),
                "session_ids": open_ids,
            },
        )
    return open_ids


def _after_replace(
    report,
    open_ids: list[str],
    play: PlayContainer | None,
    loc: LocalizationContainer | None,
    world_id: str,
) -> None:
    """What follows a replace: close the confirmed sessions, and drop the old world's
    canonical translations (U5 Q4=A). The two are independent — the purge must not sit
    behind the session step's early return, or the common replace with no open
    session would skip it (plan review FD R-13). Six routes share five call sites
    (``file`` and ``file/upload`` go through ``_import``)."""
    _close_if_replaced(report, open_ids, play)
    if getattr(report, "replaced", False):
        purge_translations(loc, kind="knowledge", world_id=world_id)


def _close_if_replaced(report, open_ids: list[str], play: PlayContainer | None) -> None:
    """After a successful replace, close the sessions the caller confirmed.

    U4 made ``close_session`` refuse while a turn run holds the session, and this runs
    *after* the world was already replaced — an unhandled refusal answered 500 and left
    the report without ``closed_session_ids`` (code review U4-2 #3). A session we cannot
    close is reported instead: its next turn stops at the boundary anyway (BR-U4-11).
    """
    if play is None or not open_ids or not getattr(report, "replaced", False):
        report.closed_session_ids = []
        return
    closed: list[str] = []
    busy: list[str] = []
    for sid in open_ids:
        try:
            play.sessions.close_session(sid)
            closed.append(sid)
        except TurnInProgressError:
            busy.append(sid)
        except LookupError:  # already gone
            closed.append(sid)
    report.closed_session_ids = closed
    if busy:
        logger.warning(
            "world replaced but %d session(s) were mid-turn and stay open: %s",
            len(busy),
            ", ".join(busy),
        )
        report.warnings = list(getattr(report, "warnings", [])) + [
            BuildWarning(
                stage="sessions",
                message=f"session {sid} was mid-turn and could not be closed",
                severity="warning",
            )
            for sid in busy
        ]


# --- build ------------------------------------------------------------------- #
@router.post("/worlds/{world_id}/build", response_model=BuildReport)
def build_world(
    world_id: str,
    inputs: WorldInputs,
    replace: bool = True,
    confirm: bool = False,
    w: WorldContainer = Depends(get_world),
    play: PlayContainer | None = Depends(get_play_optional),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> BuildReport:
    """Build from JSON inputs (images base64-encoded, RE A7)."""
    builder = _need(w.builder, "world build (LLM provider)")
    open_ids = _open_sessions(world_id, confirm, play) if replace else []
    try:
        report = builder.build(world_id, inputs, replace=replace)
    except WorldExistsError as exc:
        raise http_error(exc) from exc
    _after_replace(report, open_ids, play, loc, world_id)
    return report


@router.post("/worlds/{world_id}/build/upload", response_model=BuildReport)
def build_world_upload(
    world_id: str,
    memos: list[UploadFile] = File(default=[]),
    maps: list[UploadFile] = File(default=[]),
    images: list[UploadFile] = File(default=[]),
    name: str | None = Form(default=None),
    description: str | None = Form(default=None),
    replace: bool = Form(default=True),
    confirm: bool = Form(default=False),
    w: WorldContainer = Depends(get_world),
    play: PlayContainer | None = Depends(get_play_optional),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> BuildReport:
    """Build from uploaded files (multipart): memos (text), maps (JSON), images (map).

    A sync route: FastAPI runs it in the threadpool, so a minutes-long build never
    blocks the single worker's event loop (review #10)."""
    builder = _need(w.builder, "world build (LLM provider)")
    structured: list[dict] = []
    for f in maps:
        try:
            structured.append(json.loads(f.file.read().decode("utf-8")))
        except (UnicodeDecodeError, ValueError) as exc:
            raise HTTPException(
                status_code=422, detail=f"map {f.filename!r} is not JSON: {exc}"
            ) from exc
    inputs = WorldInputs(
        memos=[f.file.read().decode("utf-8", errors="replace") for f in memos],
        structured_maps=structured,
        map_images=[base64.b64encode(f.file.read()).decode("ascii") for f in images],
        name=name,
        description=description,
    )
    open_ids = _open_sessions(world_id, confirm, play) if replace else []
    try:
        report = builder.build(world_id, inputs, replace=replace)
    except WorldExistsError as exc:
        raise http_error(exc) from exc
    _after_replace(report, open_ids, play, loc, world_id)
    return report


@router.get("/worlds/{world_id}/graph", response_model=GraphSummary)
def graph_summary(world_id: str, shared: SharedContainer = Depends(get_shared)) -> GraphSummary:
    graph = shared.graph
    if graph is None:
        raise HTTPException(status_code=503, detail="graph repository unavailable")
    regions = graph.find_nodes(world_id, "Region")
    return GraphSummary(
        world_id=world_id,
        region_count=len(regions),
        entity_count=len(graph.find_nodes(world_id, "Entity")),
        knowledge_count=len(graph.find_nodes(world_id, "Knowledge")),
        prior_count=len(graph.find_nodes(world_id, "WikiPrior")),
        region_ids=[n.id for n in regions],
    )


# --- world list -------------------------------------------------------------- #
@router.get("/worlds", response_model=list[WorldInfo])
def list_worlds(
    w: WorldContainer = Depends(get_world),
    play: PlayContainer | None = Depends(get_play_optional),
) -> list[WorldInfo]:
    """Every stored world with its meta (BR-U2-24); pre-U2 worlds show ``name=id``. The
    rows come from ``WorldCatalog`` (U3, unchanged response); play adds open sessions."""
    catalog = _need(w.catalog, "world catalog")
    out: list[WorldInfo] = []
    for row in catalog.list_worlds():
        open_sessions = None
        if play is not None:
            open_sessions = sum(
                1 for s in play.sessions.list_sessions(row.id) if str(s.status) == "open"
            )
        out.append(WorldInfo(**row.model_dump(), open_sessions=open_sessions))
    return out


@router.get("/worlds/{world_id}/export")
def export_world(world_id: str, w: WorldContainer = Depends(get_world)) -> dict:
    """Compatibility: the v1 World File as JSON plus the legacy top-level ``world_id``."""
    try:
        return _need(w.exporter, "world export").export_world(world_id)
    except LookupError as exc:
        raise http_error(exc) from exc


@router.get("/worlds/{world_id}/file")
def get_world_file(world_id: str, w: WorldContainer = Depends(get_world)) -> Response:
    """Download the World File v1 (US-6.2)."""
    try:
        file = _need(w.exporter, "world export").export(world_id)
    except LookupError as exc:
        raise http_error(exc) from exc
    ascii_name = re.sub(r"[^A-Za-z0-9._-]", "_", world_id) or "world"
    utf8_name = quote(f"{world_id}.world.json", safe="")
    return Response(
        content=to_json_bytes(file),
        media_type="application/json",
        headers={  # RFC 5987: non-ASCII world ids (review #13)
            "Content-Disposition": f'attachment; filename="{ascii_name}.world.json"; '
            f"filename*=UTF-8''{utf8_name}"
        },
    )


def _import(
    world_id: str,
    raw: Any,
    *,
    replace: bool,
    confirm: bool,
    remap: bool,
    w: WorldContainer,
    play: PlayContainer | None,
    loc: LocalizationContainer | None,
) -> ImportReport:
    importer = _need(w.importer, "world import")
    try:
        file = WorldFile.parse(raw)
    except UnsupportedWorldFile as exc:
        raise http_error(exc) from exc
    open_ids = _open_sessions(world_id, confirm, play) if replace else []
    try:
        report = importer.import_(world_id, file, replace=replace, force_remap=remap)
    except WorldExistsError as exc:
        raise http_error(exc) from exc
    _after_replace(report, open_ids, play, loc, world_id)
    return report


@router.post("/worlds/{world_id}/file", response_model=ImportReport)
def import_world_file(
    world_id: str,
    raw: dict = Body(...),
    replace: bool = True,
    confirm: bool = False,
    remap: bool = False,
    w: WorldContainer = Depends(get_world),
    play: PlayContainer | None = Depends(get_play_optional),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> ImportReport:
    """Load a World File (JSON body) into ``world_id`` (US-6.3). ``remap=true`` forces id
    remapping (recovery from an id collision, BR-U2-4)."""
    return _import(
        world_id, raw, replace=replace, confirm=confirm, remap=remap, w=w, play=play, loc=loc
    )


@router.post("/worlds/{world_id}/file/upload", response_model=ImportReport)
def import_world_file_upload(
    world_id: str,
    file: UploadFile = File(...),
    replace: bool = Form(default=True),
    confirm: bool = Form(default=False),
    remap: bool = Form(default=False),
    w: WorldContainer = Depends(get_world),
    play: PlayContainer | None = Depends(get_play_optional),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> ImportReport:
    """Load a World File uploaded as multipart (sync route, see build_world_upload)."""
    try:
        raw = json.loads(file.file.read().decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"not a JSON file: {exc}") from exc
    return _import(
        world_id, raw, replace=replace, confirm=confirm, remap=remap, w=w, play=play, loc=loc
    )


# --- demo worlds ------------------------------------------------------------- #
@router.get("/demos", response_model=list[DemoInfo])
def list_demos(w: WorldContainer = Depends(get_world)) -> list[DemoInfo]:
    return _need(w.demo, "demo worlds").list()


@router.post("/worlds/{world_id}/demo/{name}", response_model=ImportReport)
def load_demo_world(
    world_id: str,
    name: str,
    replace: bool = True,
    confirm: bool = False,
    w: WorldContainer = Depends(get_world),
    play: PlayContainer | None = Depends(get_play_optional),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> ImportReport:
    """Load a packaged demo World File — no LLM call (FR-B3, BR-U2-28)."""
    demo = _need(w.demo, "demo worlds")
    try:
        demo.info(name)  # validate the name before the session gate (review #6)
    except LookupError as exc:
        raise http_error(exc) from exc
    open_ids = _open_sessions(world_id, confirm, play) if replace else []
    try:
        report = demo.load(name, world_id, replace=replace)
    except (LookupError, WorldExistsError) as exc:
        raise http_error(exc) from exc
    _after_replace(report, open_ids, play, loc, world_id)
    return report


@router.post("/worlds/{world_id}/demo/{name}/build", response_model=BuildReport)
def build_demo_world_from_sources(
    world_id: str,
    name: str,
    replace: bool = True,
    confirm: bool = False,
    with_map: bool = True,
    w: WorldContainer = Depends(get_world),
    play: PlayContainer | None = Depends(get_play_optional),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> BuildReport:
    """Development path: build the demo from its raw sources through the LLM pipeline
    (``with_map=false`` skips the map image / VLM)."""
    demo = _need(w.demo, "demo worlds")
    _need(w.builder, "world build (LLM provider)")
    try:
        demo.info(name)
    except LookupError as exc:
        raise http_error(exc) from exc
    open_ids = _open_sessions(world_id, confirm, play) if replace else []
    try:
        report = demo.build_from_sources(name, world_id, replace=replace, include_map=with_map)
    except (LookupError, WorldExistsError) as exc:
        raise http_error(exc) from exc
    _after_replace(report, open_ids, play, loc, world_id)
    return report


# --- wiki ------------------------------------------------------------------ #
@router.post("/worlds/{world_id}/priors", response_model=WikiPrior)
def upsert_prior(
    world_id: str, prior: WikiPrior, w: WorldContainer = Depends(get_world)
) -> WikiPrior:
    if prior.world_id != world_id:
        raise HTTPException(status_code=400, detail="prior.world_id must match path world_id")
    return _need(w.wiki_admin, "wiki admin (LLM provider)").upsert_prior(prior)


@router.get("/worlds/{world_id}/related-priors", response_model=list[WikiPrior])
def related_priors(
    world_id: str,
    query: str | None = None,
    k: int = 10,
    w: WorldContainer = Depends(get_world),
) -> list[WikiPrior]:
    """Designer-only cross-world reference (in-progress module, FR-I)."""
    return _need(w.cross_world, "cross-world wiki (LLM provider)").search_related_priors(
        world_id, query=query, k=k
    )


# --- edits ------------------------------------------------------------------ #
@router.put("/worlds/{world_id}/regions/{region_id}", response_model=Region)
def upsert_region(
    world_id: str, region_id: str, region: Region, w: WorldContainer = Depends(get_world)
) -> Region:
    return _need(w.editors, "world editor").regions.upsert_region(region)


@router.put("/worlds/{world_id}/knowledge/{knowledge_id}", response_model=Knowledge)
def upsert_knowledge(
    world_id: str, knowledge_id: str, knowledge: Knowledge, w: WorldContainer = Depends(get_world)
) -> Knowledge:
    return _need(w.editors, "world editor").knowledge.upsert_knowledge(knowledge)


# --- augmentation runs (U3 BLM §4.3 〔Step 1.3 정정〕) ---------------------------- #
_AUG_ERRORS = (LookupError, ValueError, AugmentationConflict)


@router.post("/worlds/{world_id}/augmentation/runs", response_model=AugmentationRun)
def start_augmentation(world_id: str, w: WorldContainer = Depends(get_world)) -> AugmentationRun:
    """Without an LLM the run asks template questions and skips wiki conflicts (NFR-4)."""
    try:
        return _need(w.augmentation, "augmentation").start_run(world_id)
    except LookupError as exc:  # unknown / empty world (loader) -> 404
        raise http_error(exc) from exc


@router.get("/augmentation/runs/{run_id}", response_model=AugmentationRun)
def get_augmentation(run_id: str, w: WorldContainer = Depends(get_world)) -> AugmentationRun:
    """Read a kept run again; 404 after a restart (runs live in memory, BR-U3-42)."""
    run = _need(w.augmentation, "augmentation").get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"augmentation run not found: {run_id}")
    return run


@router.post("/augmentation/runs/{run_id}/answer", response_model=AnswerResult)
def answer_augmentation(
    run_id: str, answer: AugmentationAnswer, w: WorldContainer = Depends(get_world)
) -> AnswerResult:
    try:
        return _need(w.augmentation, "augmentation").answer(run_id, answer)
    except _AUG_ERRORS as exc:
        raise http_error(exc) from exc


@router.post("/augmentation/runs/{run_id}/revert", response_model=AugmentationRun)
def revert_augmentation(
    run_id: str, change_id: str, w: WorldContainer = Depends(get_world)
) -> AugmentationRun:
    """200 + the run detected again; 409 when already undone, not the latest, or the
    target was edited outside the run."""
    try:
        return _need(w.augmentation, "augmentation").revert(run_id, change_id)
    except _AUG_ERRORS as exc:
        raise http_error(exc) from exc


@router.post("/augmentation/runs/{run_id}/unignore", response_model=AugmentationRun)
def unignore_augmentation(
    run_id: str, body: UnignoreIn, w: WorldContainer = Depends(get_world)
) -> AugmentationRun:
    """Ask an ignored issue again (FD 검토 R-08); 409 on a stopped run."""
    try:
        return _need(w.augmentation, "augmentation").unignore(run_id, body.issue_key)
    except _AUG_ERRORS as exc:
        raise http_error(exc) from exc
