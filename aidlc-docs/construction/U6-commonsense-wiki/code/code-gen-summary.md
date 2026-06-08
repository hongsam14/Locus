# U6 Commonsense Wiki (build) — Code Generation Summary

**Date**: 2026-06-08
**Stories**: US-1.5 (real-world ingest), US-5.1 (persist), US-5.2 (edit), US-5.3 (provenance). FR-E/A6, SC supporting.
**Verification**: 67 tests PASS (58 prior + 9 U6); ruff + black clean. Offline (pipeline/providers/repos mocked).

## Created files
- `locus/storage/graph_mapping.py` (**shared, pure**) — domain → Node/Edge/SearchDoc (nodes for Region/Entity/Knowledge/Rumor/WikiPrior; CONTAINS/CONNECTED_TO/SCOPED_TO/ABOUT/DERIVED_FROM/RELATED_TO/DISTORTED_FROM edges; search docs). Flattens provenance/attributes to Neo4j-safe primitives. Reused by U9.
- `locus/commonsense_wiki/schemas.py` — `PriorSuggestion`, `PriorBatch`.
- `locus/commonsense_wiki/distiller.py` — `PriorDistiller` (LLM → WikiPriors, graceful, drops invalid).
- `locus/commonsense_wiki/builder.py` — `WikiBuilder.build_wiki` (reuse IngestionService→TopologyBuilder→OntologyBuilder→PriorDistiller → persist twin + priors to `__realworld__`, embed+index, append).
- `locus/commonsense_wiki/admin.py` — `WikiAdmin.upsert_prior` / `list_priors`.
- `locus/commonsense_wiki/bundled.py` — `load_bundled_realworld()` (Earth-like memo + map).
- `examples/realworld_sample/` — `README.md`, `memo.txt`, `map.json`.

## Modified files (additive)
- `locus/models/reports.py` + `__init__` — `WikiBuildReport`.
- `locus/commonsense_wiki/__init__.py` — re-export builder/admin/distiller/bundled.

## Created tests (`tests/commonsense_wiki/test_wiki_build.py`)
graph_mapping (flatten provenance/attributes, contains/scope/connection edges, wikiprior doc meta), distiller (build + drop-invalid + graceful), WikiBuilder (persists twin nodes + priors, indexes), WikiAdmin upsert/list, bundled loader. Existing U1 lookup tests still green.

## Key realizations
- **Digital twin (Q1=B)**: real-world inputs flow through the SAME pipeline into `__realworld__`; WikiPriors are distilled on top (Q3=A) and indexed so U1 `CommonsenseWiki.lookup_*` finds them.
- **graph_mapping** centralizes domain→storage conversion (Neo4j primitive flattening) — shared with U9.
- **append (Q5=B)**, `__realworld__` isolation, no self-wiki injection during build (BR-U6-12), full graceful degradation.

## Stage notes
- NFR-R / NFR-D / Infrastructure Design SKIPPED for U6 (inherits U1 + shared infra).
- Live persistence to real Neo4j/OpenSearch validated in Build & Test.
