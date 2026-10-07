"""Locus CLI.

Commands: ``init-schema``, ``world build|export|import|demo|list`` (U2), plus the
pre-U2 aliases ``build-world`` and ``export``. Composition goes through the boundary
``assemble_*`` functions, so each command connects only the resources it needs.
Replacing a world with open sessions needs ``--force`` (NFR-9, BR-U2-26); a report
that is not ``ok`` exits 1 (BR-U2-13).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from locus.knowledge.cache import WorldCache
from locus.knowledge.loader import WorldLoader
from locus.localization.storage.schema import ensure_localization_schema
from locus.localization.wiring import assemble_localization
from locus.play.session_service import SessionService
from locus.play.storage.postgres_repo import PostgresPlayRepository
from locus.play.storage.schema import ensure_play_schema
from locus.shared.config import Settings, get_settings
from locus.shared.models.i18n import SOURCE_LANG
from locus.shared.storage.schema import ensure_world_schema
from locus.shared.wiring import SharedContainer, assemble_shared
from locus.world.build import WorldBuilder, WorldExistsError
from locus.world.demo import DemoWorlds
from locus.world.ingestion.service import WorldInputs
from locus.world.worldfile import (
    UnsupportedWorldFile,
    WorldFile,
    WorldFileExporter,
    WorldFileImporter,
    to_json_bytes,
)


def _load_inputs(path: str | None, demo: str | None) -> WorldInputs:
    """Build inputs from a JSON file, or from a manifest demo's sources (U8 BR-U8-4)."""
    if demo:
        try:
            return DemoWorlds().sources(demo)
        except LookupError as exc:
            raise SystemExit(str(exc)) from exc
    if path:
        with open(path, encoding="utf-8") as fh:
            return WorldInputs(**json.load(fh))
    raise SystemExit("provide --inputs <file.json> or --demo <name>")


def _demo_name(args: argparse.Namespace) -> str | None:
    """``world build --demo <name>``; the one-cycle alias ``build-world --demo`` takes the
    first manifest demo that has sources (no demo name in code, BR-U8-1)."""
    if getattr(args, "demo", None):
        return str(args.demo)
    if getattr(args, "demo_alias", False):
        for info in DemoWorlds().list():
            if info.has_sources:
                return info.name
        raise SystemExit("no packaged demo has sources")
    return None


# --- composition helpers (CLI is a composition root) ------------------------------ #
def _world_services(shared: SharedContainer, settings: Settings, *, with_builder: bool):
    assert shared.graph is not None
    cache = WorldCache(WorldLoader(shared.graph))
    exporter = WorldFileExporter(cache)
    if shared.search is None:  # export / list only
        return exporter, None, None, None
    importer = WorldFileImporter(
        shared.graph,
        shared.search,
        shared.embedding,
        cache,
        exporter=exporter,
        backup_dir=settings.backup_dir,
    )
    builder = None
    if with_builder:
        if shared.factory is None:
            raise SystemExit("building needs an LLM provider (OPENAI_API_KEY)")
        builder = WorldBuilder.from_factory(
            shared.factory,
            shared.graph,
            shared.search,
            cache=cache,
            exporter=exporter,
            backup_dir=settings.backup_dir,
            tuning=settings.world_tuning(),  # U7 review #3: the CLI builds with the env knobs too
        )
    return exporter, importer, DemoWorlds(importer, builder), builder


def _session_service(shared: SharedContainer) -> SessionService | None:
    """Play boundary for the open-session check; None when PostgreSQL is not configured."""
    if shared.sql_engine is None or shared.graph is None:
        return None
    # U4: the session service reads the canonical world through a snapshot source
    # (world existence / regions); the CLI only lists and closes sessions here.
    return SessionService(
        PostgresPlayRepository(engine=shared.sql_engine), WorldCache(WorldLoader(shared.graph))
    )


def _guard_open_sessions(shared: SharedContainer, world_id: str, *, force: bool) -> list[str]:
    """Exit 1 when the world has open sessions and --force was not given (BR-U2-26).
    Returns the ids to close once the replace has really happened (nothing closed yet)."""
    sessions = _session_service(shared)
    if sessions is None:
        return []
    open_ids = [s.id for s in sessions.open_sessions(world_id)]
    if open_ids and not force:
        raise SystemExit(
            f"world {world_id!r} has {len(open_ids)} open session(s): {', '.join(open_ids)}. "
            "Re-run with --force to close them and replace the world."
        )
    return open_ids


def _print_report(report, open_ids: list[str], shared: SharedContainer) -> int:
    """Close the confirmed sessions only after a real replace; print; exit 1 unless ok."""
    closed: list[str] = []
    sessions = _session_service(shared) if open_ids else None
    if sessions is not None and getattr(report, "replaced", False):
        for sid in open_ids:
            sessions.close_session(sid)
        closed = list(open_ids)
    report.closed_session_ids = closed
    print(report.model_dump_json(indent=2))
    return 0 if report.ok else 1


# --- commands ---------------------------------------------------------------- #
def cmd_init_schema(args: argparse.Namespace) -> int:
    want_world, want_play, want_l10n = args.world, args.play, args.localization
    if not (want_world or want_play or want_l10n):
        want_world = want_play = want_l10n = True
    s = get_settings()
    done: list[str] = []
    shared = assemble_shared(
        s, graph=want_world, search=want_world, llm=False, sql=(want_play or want_l10n)
    )
    try:
        if want_world:
            if shared.graph is None or shared.search is None:
                raise SystemExit("Neo4j / OpenSearch not configured")
            ensure_world_schema(shared.graph, shared.search)
            done.append("world (Neo4j constraints/indexes + OpenSearch index)")
        if want_play or want_l10n:
            if shared.sql_engine is None:
                raise SystemExit("SESSION_DB_URL (PostgreSQL) not configured")
            if want_play:
                ensure_play_schema(shared.sql_engine)
                done.append("play (PostgreSQL session tables)")
            if want_l10n:
                ensure_localization_schema(shared.sql_engine)
                done.append("localization (PostgreSQL translations table)")
    finally:
        shared.close()
    print("Schema initialized: " + "; ".join(done))
    return 0


def cmd_world_build(args: argparse.Namespace) -> int:
    settings = get_settings()
    shared = assemble_shared(settings)
    try:
        _e, _i, _d, builder = _world_services(shared, settings, with_builder=True)
        assert builder is not None
        inputs = _load_inputs(args.inputs, _demo_name(args))  # fail before touching sessions
        open_ids = (
            _guard_open_sessions(shared, args.world, force=args.force) if args.replace else []
        )
        try:
            report = builder.build(args.world, inputs, replace=args.replace)
        except WorldExistsError as exc:
            raise SystemExit(f"{exc}; pass --replace to rebuild it") from exc
        return _print_report(report, open_ids, shared)
    finally:
        shared.close()


def cmd_world_export(args: argparse.Namespace) -> int:
    settings = get_settings()
    shared = assemble_shared(settings, search=False, llm=False, sql=False)
    try:
        exporter, *_ = _world_services(shared, settings, with_builder=False)
        try:
            file = exporter.export(args.world)
        except LookupError as exc:
            raise SystemExit(str(exc)) from exc
        Path(args.out).write_bytes(to_json_bytes(file))
        print(f"Exported world '{args.world}' -> {args.out} ({file.counts()})")
        return 0
    finally:
        shared.close()


def cmd_world_import(args: argparse.Namespace) -> int:
    settings = get_settings()
    shared = assemble_shared(settings, llm=False)
    try:
        _e, importer, *_ = _world_services(shared, settings, with_builder=False)
        assert importer is not None
        try:
            file = WorldFile.parse(json.loads(Path(args.file).read_text(encoding="utf-8")))
        except (OSError, ValueError, UnsupportedWorldFile) as exc:
            raise SystemExit(f"cannot read world file: {exc}") from exc
        open_ids = (
            _guard_open_sessions(shared, args.world, force=args.force) if args.replace else []
        )
        try:
            report = importer.import_(
                args.world, file, replace=args.replace, force_remap=args.remap
            )
        except WorldExistsError as exc:
            raise SystemExit(f"{exc}; pass --replace to overwrite it") from exc
        return _print_report(report, open_ids, shared)
    finally:
        shared.close()


def cmd_world_demo(args: argparse.Namespace) -> int:
    settings = get_settings()
    if args.list:
        for info in DemoWorlds().list():
            print(f"{info.name}\t{info.title}\t{info.description or ''}")
        return 0
    if not (args.name and args.world):
        raise SystemExit("provide --list, or --name <demo> --world <world_id>")
    shared = assemble_shared(settings, llm=False)
    try:
        _e, _i, demos, _b = _world_services(shared, settings, with_builder=False)
        assert demos is not None
        try:
            demos.info(args.name)  # validate the name before the session gate
        except LookupError as exc:
            raise SystemExit(str(exc)) from exc
        open_ids = (
            _guard_open_sessions(shared, args.world, force=args.force) if args.replace else []
        )
        try:
            report = demos.load(args.name, args.world, replace=args.replace)
        except LookupError as exc:
            raise SystemExit(str(exc)) from exc
        except WorldExistsError as exc:
            raise SystemExit(f"{exc}; pass --replace to overwrite it") from exc
        code = _print_report(report, open_ids, shared)
        _seed_demo_translations(shared, settings, demos, args.name, args.world, report)
        return code
    finally:
        shared.close()


def _seed_demo_translations(
    shared: SharedContainer,
    settings: Settings,
    demos: DemoWorlds,
    name: str,
    world_id: str,
    report,
) -> None:
    """After a demo load, seed its translations as the API does (V3, BR-V3-28). Calls the
    services directly — ``locus`` never imports ``api`` (code plan memo R-03). The one
    line goes to stderr, so stdout stays the JSON report (memo R-02); it never changes
    the exit code. Order: off -> no database -> database unreachable -> seed (memo R-01)."""

    def say(message: str) -> None:
        print(f"translations: {message}", file=sys.stderr)

    if not settings.translation_enabled:
        return say("off")
    if shared.sql_engine is None:
        return say("skipped (no database configured)")
    try:
        loc = assemble_localization(shared)
    except Exception as exc:  # ensure_schema could not reach PostgreSQL
        return say(f"skipped (database unreachable: {type(exc).__name__})")
    try:
        service = loc.translations
        if service is None:
            return say("skipped (no translation service)")
        if not getattr(report, "ok", False):
            return say("skipped (the load was not ok)")
        if getattr(report, "replaced", False):
            try:
                service.purge(world_id=world_id)
                service.purge(kind="world", ids=[world_id])
            except Exception as exc:
                say(f"purge failed ({type(exc).__name__}); seeding anyway")
        remapped = bool(getattr(report, "remapped", False))
        parts: list[str] = []
        for lang in demos.translation_langs(name):
            if lang == SOURCE_LANG or lang not in settings.supported_langs:
                continue
            entries = demos.translations(name, lang, target_world_id=world_id, remapped=remapped)
            texts = demos.texts(name, target_world_id=world_id, remapped=remapped)
            got = service.seed(entries, lang=lang, current_text=texts, world_id=world_id)
            parts.append(f"{lang} seeded {got.seeded}, stale {got.stale}, unknown {got.unknown}")
        say("; ".join(parts) or "none in this demo")
    except Exception as exc:
        say(f"failed ({type(exc).__name__}: {exc})")
    finally:
        loc.close()


def cmd_world_list(args: argparse.Namespace) -> int:
    settings = get_settings()
    shared = assemble_shared(settings, search=False, llm=False, sql=False)
    try:
        assert shared.graph is not None
        from locus.world.editor import WorldCatalog

        for row in WorldCatalog(shared.graph).list_worlds():  # the API's list (U3 C7)
            print(
                f"{row.id}\t{row.name}\tregions={row.region_count}\tupdated={row.updated_at or '-'}"
            )
        return 0
    finally:
        shared.close()


# --- parser ------------------------------------------------------------------ #
def _add_replace_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--replace",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="replace an existing world (default) / --no-replace to fail if it exists",
    )
    p.add_argument(
        "--force", action="store_true", help="close open sessions of the world before replacing"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="locus", description="Locus CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_schema = sub.add_parser(
        "init-schema",
        help="Create schemas: --world (Neo4j+OpenSearch), --play / --localization (PostgreSQL); "
        "no flag = all",
    )
    p_schema.add_argument("--world", action="store_true")
    p_schema.add_argument("--play", action="store_true")
    p_schema.add_argument("--localization", action="store_true")
    p_schema.set_defaults(func=cmd_init_schema)

    p_world = sub.add_parser("world", help="Build, save, load and list worlds")
    wsub = p_world.add_subparsers(dest="world_command", required=True)

    p_build = wsub.add_parser("build", help="Build a world from sources (LLM)")
    p_build.add_argument("--world", required=True, help="world id")
    p_build.add_argument("--inputs", help="JSON file with WorldInputs (images base64)")
    p_build.add_argument(
        "--demo", metavar="NAME", help="build from a packaged demo's sources (see `demo --list`)"
    )
    _add_replace_flags(p_build)
    p_build.set_defaults(func=cmd_world_build)

    p_export = wsub.add_parser("export", help="Save a world as a World File (v1)")
    p_export.add_argument("--world", required=True)
    p_export.add_argument("--out", required=True, help="output .world.json")
    p_export.set_defaults(func=cmd_world_export)

    p_import = wsub.add_parser("import", help="Load a World File (no LLM)")
    p_import.add_argument("--world", required=True, help="target world id")
    p_import.add_argument("--file", required=True, help="World File (v1) or legacy export JSON")
    p_import.add_argument(
        "--remap", action="store_true", help="force id remapping (id collision recovery)"
    )
    _add_replace_flags(p_import)
    p_import.set_defaults(func=cmd_world_import)

    p_demo = wsub.add_parser("demo", help="List or load packaged demo worlds (no LLM)")
    p_demo.add_argument("--list", action="store_true")
    p_demo.add_argument("--name", help="demo name (see --list)")
    p_demo.add_argument("--world", help="target world id")
    _add_replace_flags(p_demo)
    p_demo.set_defaults(func=cmd_world_demo)

    p_list = wsub.add_parser("list", help="List stored worlds")
    p_list.set_defaults(func=cmd_world_list)

    # pre-U2 aliases (one cycle)
    p_alias_build = sub.add_parser("build-world", help="alias of `world build`")
    p_alias_build.add_argument("--world", required=True)
    p_alias_build.add_argument("--inputs")
    p_alias_build.add_argument("--demo", dest="demo_alias", action="store_true")
    _add_replace_flags(p_alias_build)
    p_alias_build.set_defaults(func=cmd_world_build)

    p_alias_export = sub.add_parser("export", help="alias of `world export`")
    p_alias_export.add_argument("--world", required=True)
    p_alias_export.add_argument("--out", required=True)
    p_alias_export.set_defaults(func=cmd_world_export)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
