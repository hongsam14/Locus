"""Locus CLI (U9). Commands: init-schema, build-wiki, build-world, export."""

from __future__ import annotations

import argparse
import json
import sys

from .commonsense_wiki import PriorDistiller, WikiBuilder, load_bundled_realworld
from .config import get_settings
from .demo import load_demo_world
from .ingestion.service import IngestionService, WorldInputs
from .llm.factory import ProviderFactory
from .ontology.builder import OntologyBuilder
from .query import WorldLoader
from .services import Exporter, PipelineOrchestrator
from .storage import Neo4jGraphRepository, OpenSearchRepository, SchemaInitializer
from .topology.builder import TopologyBuilder


def _repos():
    s = get_settings()
    graph = Neo4jGraphRepository(
        uri=s.neo4j_uri, user=s.neo4j_user, password=s.neo4j_password.get_secret_value()
    )
    search = OpenSearchRepository(
        url=s.opensearch_url, index=s.opensearch_index, vector_dimension=s.embedding_dimension
    )
    graph.connect()
    search.connect()
    return s, graph, search


def _load_inputs(path: str | None, demo: bool) -> WorldInputs:
    if demo:
        return load_demo_world()
    if path:
        with open(path, encoding="utf-8") as fh:
            return WorldInputs(**json.load(fh))
    raise SystemExit("provide --inputs <file.json> or --demo")


def cmd_init_schema(_args: argparse.Namespace) -> int:
    _s, graph, search = _repos()
    try:
        SchemaInitializer(graph, search).initialize()
        print("Schema initialized: Neo4j constraints/indexes + OpenSearch index ready.")
    finally:
        graph.disconnect()
        search.disconnect()
    return 0


def cmd_build_wiki(args: argparse.Namespace) -> int:
    s, graph, search = _repos()
    factory = ProviderFactory(s)
    llm, embedding = factory.llm(), factory.embedding()
    builder = WikiBuilder(
        IngestionService.from_factory(factory),
        TopologyBuilder(wiki=None),
        OntologyBuilder(llm=llm, embedding=embedding, wiki=None),
        PriorDistiller(llm),
        graph,
        search,
        embedding,
    )
    inputs = (
        WorldInputs(**json.load(open(args.inputs, encoding="utf-8")))
        if args.inputs
        else load_bundled_realworld()
    )
    try:
        report = builder.build_wiki(inputs)
        print(f"Wiki built: {report.model_dump_json()}")
    finally:
        graph.disconnect()
        search.disconnect()
    return 0


def cmd_build_world(args: argparse.Namespace) -> int:
    s, graph, search = _repos()
    factory = ProviderFactory(s)
    orch = PipelineOrchestrator.from_factory(factory, graph, search)
    inputs = _load_inputs(args.inputs, args.demo)
    try:
        report = orch.build_world(args.world, inputs)
        print(f"World built: {report.model_dump_json()}")
    finally:
        graph.disconnect()
        search.disconnect()
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    _s, graph, search = _repos()
    try:
        data = Exporter(WorldLoader(graph)).export_world(args.world)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        print(f"Exported world '{args.world}' -> {args.out}")
    finally:
        graph.disconnect()
        search.disconnect()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="locus", description="Locus CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "init-schema", help="Create Neo4j constraints/indexes + OpenSearch index"
    ).set_defaults(func=cmd_init_schema)

    p_wiki = sub.add_parser("build-wiki", help="Build the Common-sense Wiki (bundled or --inputs)")
    p_wiki.add_argument("--inputs", help="JSON file with real-world WorldInputs")
    p_wiki.set_defaults(func=cmd_build_wiki)

    p_world = sub.add_parser("build-world", help="Build a game world graph")
    p_world.add_argument("--world", required=True, help="world id")
    p_world.add_argument("--inputs", help="JSON file with WorldInputs")
    p_world.add_argument("--demo", action="store_true", help="use the bundled demo world")
    p_world.set_defaults(func=cmd_build_world)

    p_export = sub.add_parser("export", help="Export a world graph to JSON")
    p_export.add_argument("--world", required=True, help="world id")
    p_export.add_argument("--out", required=True, help="output JSON file")
    p_export.set_defaults(func=cmd_export)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
