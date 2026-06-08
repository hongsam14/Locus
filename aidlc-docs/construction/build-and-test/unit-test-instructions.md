# Unit Test Execution — Locus

## Run
```bash
source .venv/bin/activate
pytest                       # all unit tests + coverage (pyproject addopts: --cov=locus)
pytest tests/ontology        # a single unit's tests
ruff check locus/ api/ tests/
black --check locus/ api/ tests/
```

## Expected (current)
- **93 tests pass, 0 failures**; coverage ≈ 82% (`--cov=locus`).
- 3 warnings (FastAPI `on_event` deprecation) — acceptable.
- ruff + black clean.

## Coverage by unit (tests/)
| Unit | tests/ dir | focus |
|---|---|---|
| U1 Foundation | models, llm, storage, commonsense_wiki | models PBT round-trip, retry/factory, Cypher/query construction, wiki lookup fallback |
| U2 Ingestion | ingestion | mapping/merge/parse (+PBT), ingestors (mock LLM/VLM), service merge |
| U3 Topology | topology | weights (+PBT), hierarchy, edge candidates, build (mock wiki) |
| U4 Ontology | ontology | similarity/PBT, dedup (mock embed+LLM), corroboration, scope, builder |
| U5 Consensus | consensus | max-product weights (+PBT), classification, distortion |
| U6 Wiki build | commonsense_wiki | graph_mapping, distiller, builder, admin, bundled |
| U8 Query&Serving | query | reverse-mapping round-trip, loader, split/diff, QueryEngine, API (TestClient) |
| U9 Orchestration | services, query/test_authoring_api | persist_graph, orchestrator, editor, exporter, authoring API |

## On failure
1. Read pytest output (failing test + assert).
2. Fix code; re-run the single test file, then the full suite.
3. External calls (OpenAI/Neo4j/OpenSearch) are mocked — failures are logic, not connectivity.

## Notes
- **PBT (Partial)**: hypothesis covers serialization round-trips + pure numeric functions (weights, cosine, path-weights) per NFR-C2.
- All external I/O is behind ports and mocked, so the suite is fully offline.
