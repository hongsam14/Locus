# Integration Test Instructions — Locus (live walkthrough)

Tests the units working together against **real Neo4j + OpenSearch + OpenAI**. Operator-run (needs `OPENAI_API_KEY` + Docker). Unit tests already cover logic offline; this validates wiring, persistence, and the end-to-end SC-1/2/4.

## Setup
```bash
docker-compose up -d neo4j opensearch
# wait for healthy:
docker-compose ps
source .venv/bin/activate
cp env.example .env && $EDITOR .env     # set OPENAI_API_KEY; NEO4J/OPENSEARCH localhost URLs
locus init-schema                        # Neo4j constraints/indexes + OpenSearch index
```

## Scenarios

### A — Schema bootstrap (U1 infra)
- Steps: `locus init-schema`.
- Expected: prints "Schema initialized…"; Neo4j has uniqueness constraints (Region/Entity/Knowledge/Rumor/WikiPrior) + `world_id` indexes; OpenSearch `locus_search` index exists (`curl localhost:9200/locus_search`). Re-run is idempotent (no errors).

### B — Common-sense Wiki build (U6, digital twin)
- Steps: `locus build-wiki`  (bundled real-world sample).
- Expected: `WikiBuildReport` with regions/entities/knowledge/priors ≥ 1; `__realworld__` nodes in Neo4j (`MATCH (n {world_id:'__realworld__'}) RETURN labels(n), count(*)`); WikiPrior docs in OpenSearch.

### C — World build end-to-end (U2→U3→U4→persist) — **SC-1**
- Steps: `locus build-world --world aldermoor --demo`.
- Expected: `BuildReport` (regions≥5, knowledge≥ a few, corroborations_created ≥ 1 → **SC-4**). Neo4j has `world_id='aldermoor'` Region hierarchy (CONTAINS) + CONNECTED_TO (Riverton–Highcrag `blocked`, low weight). No human edits required → SC-1.

### D — Query: region knowledge + global (U8/U5) — **SC-2 setup**
- Steps: start API `uvicorn api.main:app --port 8000`; find a region id (`GET /api/authoring/worlds/aldermoor/graph` → region_ids); `GET /api/query/regions/{riverton_id}/knowledge?world_id=aldermoor`.
- Expected: 200 JSON `QueryResult`; Riverton has direct market knowledge in `unique_ids`; "sun rises in the east" appears as a **global** item (in every region); items carry scope_type/confidence/source.

### E — Shared vs unique across two regions (U8 diff) — **SC-2**
- Steps: `GET /api/query/diff?world_id=aldermoor&region_a={riverton}&region_b={highcrag}`.
- Expected: 200 `RegionDiff`; global fact in `shared_ids`; Riverton-specific market lore in `only_a_ids`. Riverton's market knowledge reaches Highcrag weakly (mountain `blocked`) → appears as rumor/unknown, not as confident shared knowledge.

### F — Authoring edit + export (U9)
- Steps: `PUT /api/authoring/worlds/aldermoor/knowledge/{id}` (edit a statement); `DELETE /api/authoring/worlds/aldermoor/nodes/{id}`; `locus export --world aldermoor --out aldermoor.json`.
- Expected: edit reflected on re-query; deleted node gone; `aldermoor.json` contains regions/entities/knowledge/scopes/connections.

### G — Knowledge augmentation Q&A (U7)
- Steps: `POST /api/authoring/worlds/aldermoor/augment/session` → returns issues→questions (e.g. empty region, low-confidence item); `POST /api/authoring/augment/{sid}/answer` with `{action:"add", statement:"...", region_id:"..."}`; `POST /api/authoring/augment/{sid}/revert?change_id=...`.
- Expected: session lists open questions; answering applies a ChangeSet (new/edited knowledge, source=augmentation) and re-detects; revert restores prior state.

### H — Web UI (U10)
- Steps: `cd web && npm run dev` (backend up); open :5173; set world `aldermoor` → Build/Load → topology overlay; drag a marker (persists position); select region → knowledge panel; run augmentation panel.
- Expected: regions render at map positions (GeoJSON/VLM/auto); blocked connection = red dashed; edits/augmentation reflected via API. See `frontend-test-instructions.md`.

## Cleanup
```bash
docker-compose down          # keep volumes
docker-compose down -v       # also wipe Neo4j/OpenSearch data
```

## Pass criteria
- A–F succeed; SC-1 (auto build), SC-2 (shared vs unique distinguished), SC-4 (≥1 corroboration) demonstrated.
- Logs show graceful handling of any low-confidence/failed extractions (warnings, not crashes).
