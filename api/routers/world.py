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
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, File, Form, Response, UploadFile

from api import uploads
from api.deps import (
    display_lang,
    get_localization,
    get_play_optional,
    get_shared,
    get_world,
    lang_settings,
)
from api.deps import need_service as _need
from api.errors import ApiError, http_error
from api.routers import world_editor
from api.schemas import (
    DemoInfoOut,
    DemoLoadOut,
    UnignoreIn,
    WorldInfo,
    WorldNamesOut,
    enrichment_for,
    purge_translations,
    purge_world_translations,
    seed_demo_translations,
    world_names,
)
from locus.localization.wiring import LocalizationContainer
from locus.play.errors import TurnInProgressError
from locus.play.wiring import PlayContainer
from locus.shared.config import Settings
from locus.shared.models import (
    BuildReport,
    GraphSummary,
    ImportReport,
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
from locus.world.build import BuildInProgressError, WorldExistsError
from locus.world.ingestion.service import WorldInputs
from locus.world.wiring import WorldContainer
from locus.world.worldfile import UnsupportedWorldFile, WorldFile, to_json_bytes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/world", tags=["world"])


def _open_sessions(world_id: str, confirm: bool, play: PlayContainer | None) -> list[str]:
    """Open sessions block a replace unless confirmed (BR-U2-25). Returns the ids that
    will be closed once the replace has actually happened; nothing is closed here, so a
    build/import that fails or never replaces leaves the sessions untouched (review #6).
    Without a play boundary nothing is checked."""
    if play is None:
        return []
    open_ids = [s.id for s in play.sessions.open_sessions(world_id)]
    # Pre-flight the turn guard: a session mid-turn cannot be closed, so admitting it
    # here let the destructive replace run and then fail on the close, after the world
    # was already gone (code review U4-2 #3, re-framed root cause).
    busy = [sid for sid in open_ids if play.guard.is_running(sid)]
    if busy:
        raise ApiError(
            409,
            {
                "message": f"world {world_id!r} has {len(busy)} session(s) mid-turn; "
                "retry once their turns finish",
                "busy_sessions": len(busy),
                "session_ids": busy,
            },
            "sessions_busy",
        )
    if open_ids and not confirm:
        raise ApiError(
            409,
            {
                "message": f"world {world_id!r} has {len(open_ids)} open session(s); "
                "pass confirm=true to close them and replace the world",
                "open_sessions": len(open_ids),
                "session_ids": open_ids,
            },
            "sessions_open",
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
    translations (U5 Q4=A; V3 BR-V3-13: every kind of the world, not only knowledge). The
    two are independent — the purge must not sit behind the session step's early
    return, or the common replace with no open session would skip it (plan review FD
    R-13). Six routes share five call sites (``file`` and ``file/upload`` go through
    ``_import``)."""
    _close_if_replaced(report, open_ids, play)
    if getattr(report, "replaced", False):
        purge_world_translations(loc, world_id)


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
    builder = _need(w.builder, "world build (LLM provider)", "llm_unavailable")
    open_ids = _open_sessions(world_id, confirm, play) if replace else []
    try:
        report = builder.build(world_id, inputs, replace=replace)
    except (WorldExistsError, BuildInProgressError) as exc:
        raise http_error(exc) from exc
    _after_replace(report, open_ids, play, loc, world_id)
    return report


@router.post("/worlds/{world_id}/build/upload", response_model=BuildReport)
def build_world_upload(
    world_id: str,
    memos: list[UploadFile] = File(default=[]),
    maps: list[UploadFile] = File(default=[]),
    images: list[UploadFile] = File(default=[]),
    concept_arts: list[UploadFile] = File(default=[]),
    name: str | None = Form(default=None),
    description: str | None = Form(default=None),
    replace: bool = Form(default=True),
    confirm: bool = Form(default=False),
    w: WorldContainer = Depends(get_world),
    play: PlayContainer | None = Depends(get_play_optional),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> BuildReport:
    """Build from uploaded files (multipart): memos (text), maps (JSON), images (map),
    concept arts (U3). Each field has a file count and size cap, memos a length cap and
    images a format check (413 / 422, nfr §1.1).

    A sync route: FastAPI runs it in the threadpool, so a minutes-long build never
    blocks the single worker's event loop (review #10)."""
    builder = _need(w.builder, "world build (LLM provider)", "llm_unavailable")
    for field, files, cap in (
        ("memos", memos, uploads.MEMO),
        ("maps", maps, uploads.MAP),
        ("images", images, uploads.MAP_IMAGE),
        ("concept_arts", concept_arts, uploads.CONCEPT_ART),
    ):
        uploads.check_count(field, files, cap)
    # sessions before reading and encoding every file (U3 review C15)
    open_ids = _open_sessions(world_id, confirm, play) if replace else []
    structured: list[dict] = []
    for f in maps:
        try:
            parsed = json.loads(uploads.read_capped("maps", f, uploads.MAP))
        except (UnicodeDecodeError, ValueError, RecursionError) as exc:  # fixed text (S07)
            raise ApiError(422, f"map {f.filename!r} is not valid JSON", "bad_map_json") from exc
        if not isinstance(parsed, dict):  # a list, string or number is no map (U3 S07)
            raise ApiError(422, f"map {f.filename!r} is not valid JSON", "bad_map_json")
        structured.append(parsed)

    def b64(data: bytes) -> str:
        return base64.b64encode(data).decode("ascii")

    inputs = WorldInputs(
        memos=[uploads.read_memo(f) for f in memos],
        structured_maps=structured,
        map_images=[b64(uploads.read_image("images", f, uploads.MAP_IMAGE)) for f in images],
        concept_arts=[
            b64(uploads.read_image("concept_arts", f, uploads.CONCEPT_ART)) for f in concept_arts
        ],
        name=name,
        description=description,
    )
    try:
        report = builder.build(world_id, inputs, replace=replace)
    except (WorldExistsError, BuildInProgressError) as exc:
        raise http_error(exc) from exc
    _after_replace(report, open_ids, play, loc, world_id)
    return report


@router.get("/worlds/{world_id}/graph", response_model=GraphSummary)
def graph_summary(world_id: str, shared: SharedContainer = Depends(get_shared)) -> GraphSummary:
    graph = shared.graph
    if graph is None:
        raise ApiError(503, "graph repository unavailable", "service_unavailable")
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
    lang: str = Depends(display_lang),
    w: WorldContainer = Depends(get_world),
    play: PlayContainer | None = Depends(get_play_optional),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> list[WorldInfo]:
    """Every stored world with its meta (BR-U2-24); pre-U2 worlds show ``name=id``. The
    rows come from ``WorldCatalog`` (U3, unchanged response); play adds open sessions,
    the translation cache the names in the display language (V3, BR-V3-23)."""
    catalog = _need(w.catalog, "world catalog")
    rows = catalog.list_worlds()
    names = enrichment_for(loc, rows, kind="world", fields=["name", "description"], lang=lang)
    out: list[WorldInfo] = []
    for row in rows:
        open_sessions = None
        if play is not None:
            open_sessions = len(play.sessions.open_sessions(row.id))
        ko = names.get(row.id, {})
        out.append(
            WorldInfo(
                **row.model_dump(),
                open_sessions=open_sessions,
                name_ko=ko.get("name"),
                description_ko=ko.get("description"),
            )
        )
    return out


@router.get("/worlds/{world_id}/names", response_model=WorldNamesOut)
def get_world_names(
    world_id: str,
    lang: str = Depends(display_lang),
    w: WorldContainer = Depends(get_world),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> WorldNamesOut:
    """The world's name map in the display language (V3, Q5=A, BLM § 8): region, NPC,
    event-seed and world text by id, cache only. 404 for a world that is not there."""
    cache = _need(w.cache, "world cache")  # 503 without one (code plan memo R-03)
    try:
        snapshot = cache.get(world_id)
    except LookupError as exc:
        raise http_error(exc) from exc
    return world_names(loc, snapshot, lang=lang)


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
    data = uploads.read_capped("file", file, uploads.WORLD_FILE)  # 20 MiB (nfr §1.1)
    try:
        raw = json.loads(data)
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:  # fixed text (NFR-6, S07)
        raise ApiError(
            422, f"{file.filename!r} is not a JSON World File", "bad_world_file"
        ) from exc
    return _import(
        world_id, raw, replace=replace, confirm=confirm, remap=remap, w=w, play=play, loc=loc
    )


# --- demo worlds ------------------------------------------------------------- #
@router.get("/demos", response_model=list[DemoInfoOut])
def list_demos(
    lang: str = Depends(display_lang), w: WorldContainer = Depends(get_world)
) -> list[DemoInfoOut]:
    """The manifest's demos (U8, BR-U8-19): the home screen draws a card for each, in the
    display language when the manifest has its text (V3, BR-V3-23)."""
    return [DemoInfoOut.of(info, lang) for info in _need(w.demo, "demo worlds").list()]


@router.post("/worlds/{world_id}/demo/{name}", response_model=DemoLoadOut)
def load_demo_world(
    world_id: str,
    name: str,
    replace: bool = True,
    confirm: bool = False,
    w: WorldContainer = Depends(get_world),
    play: PlayContainer | None = Depends(get_play_optional),
    loc: LocalizationContainer | None = Depends(get_localization),
    settings: Settings = Depends(lang_settings),
) -> DemoLoadOut:
    """Load a packaged demo World File — no LLM call (FR-B3, BR-U2-28) — then seed its
    translations: import → (replace) purge → (ok) seed (V3, BLM § 3, BR-V3-14)."""
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
    seeded = seed_demo_translations(
        loc, demo, name, world_id=world_id, report=report, langs=settings.supported_langs
    )
    return DemoLoadOut(
        **report.model_dump(exclude={"ok"}),  # ``ok`` is computed, not an input
        translations_seeded=seeded.seeded,
        translations_stale=seeded.stale,
    )


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
    _need(w.builder, "world build (LLM provider)", "llm_unavailable")
    try:
        demo.info(name)
    except LookupError as exc:
        raise http_error(exc) from exc
    open_ids = _open_sessions(world_id, confirm, play) if replace else []
    try:
        report = demo.build_from_sources(name, world_id, replace=replace, include_map=with_map)
    except (LookupError, WorldExistsError, BuildInProgressError) as exc:
        raise http_error(exc) from exc
    _after_replace(report, open_ids, play, loc, world_id)
    return report


# --- wiki ------------------------------------------------------------------ #
@router.post("/worlds/{world_id}/priors", response_model=WikiPrior)
def upsert_prior(
    world_id: str, prior: WikiPrior, w: WorldContainer = Depends(get_world)
) -> WikiPrior:
    if prior.world_id != world_id:
        raise ApiError(400, "prior.world_id must match path world_id", "invalid_request")
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
        raise ApiError(404, f"augmentation run not found: {run_id}", "not_found")
    return run


@router.post("/augmentation/runs/{run_id}/answer", response_model=AnswerResult)
def answer_augmentation(
    run_id: str,
    answer: AugmentationAnswer,
    w: WorldContainer = Depends(get_world),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> AnswerResult:
    try:
        result = _need(w.augmentation, "augmentation").answer(run_id, answer)
    except _AUG_ERRORS as exc:
        raise http_error(exc) from exc
    if result.change is not None:  # a REMOVE answer deletes knowledge (U3 review S10)
        kept = {n.id for n in result.change.nodes_after}
        gone = [
            n.id for n in result.change.nodes_before if n.label == "Knowledge" and n.id not in kept
        ]
        if gone:
            purge_translations(loc, kind="knowledge", ids=gone)
    return result


@router.post("/augmentation/runs/{run_id}/revert", response_model=AugmentationRun)
def revert_augmentation(
    run_id: str,
    change_id: str,
    w: WorldContainer = Depends(get_world),
    loc: LocalizationContainer | None = Depends(get_localization),
) -> AugmentationRun:
    """200 + the run detected again; 409 when already undone, not the latest, or the
    target was edited outside the run. Undoing an added fact purges its translations
    (U3 review S10)."""
    try:
        run = _need(w.augmentation, "augmentation").revert(run_id, change_id)
    except _AUG_ERRORS as exc:
        raise http_error(exc) from exc
    change = next((c for c in run.history if c.id == change_id), None)
    if change is not None and change.added_ids:
        purge_translations(loc, kind="knowledge", ids=list(change.added_ids))
    return run


@router.post("/augmentation/runs/{run_id}/unignore", response_model=AugmentationRun)
def unignore_augmentation(
    run_id: str, body: UnignoreIn, w: WorldContainer = Depends(get_world)
) -> AugmentationRun:
    """Ask an ignored issue again (FD 검토 R-08); 409 on a stopped run."""
    try:
        return _need(w.augmentation, "augmentation").unignore(run_id, body.issue_key)
    except _AUG_ERRORS as exc:
        raise http_error(exc) from exc


# --- the world editor (U3, BLM §7) — its own module, mounted under /api/world ---- #
router.include_router(world_editor.router)
