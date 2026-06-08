# U9 Orchestration & Authoring — Domain Entities & Contracts

결정: FD9-Q1=A(빌드→persist, 컨센서스 실시간), Q2=C(편집 포함), Q3=A, Q4=A(JSON export), Q5=A(데모).

## build_world (PipelineOrchestrator)
- Input: `world_id`, `WorldInputs`(U2). Output: `BuildReport`(U1).
- persist: graph_mapping(U6 도입) 재사용 → Neo4j 노드/엣지 + OpenSearch 색인. 컨센서스는 영속 안 함(쿼리 시점, U5).

## authoring API 계약 (Q2=C)
```
POST /api/authoring/worlds/{world_id}/build      body: WorldInputs        -> BuildReport
POST /api/authoring/wiki/build                   body: WorldInputs?(없으면 번들) -> WikiBuildReport
GET  /api/authoring/worlds/{world_id}/graph      -> GraphSummary (counts + ids)
POST /api/authoring/wiki/priors                  body: WikiPrior          -> WikiPrior (upsert)
# 편집(Q2=C)
PUT    /api/authoring/worlds/{world_id}/regions/{id}     body: Region    -> Region (upsert)
PUT    /api/authoring/worlds/{world_id}/knowledge/{id}   body: Knowledge -> Knowledge (upsert)
DELETE /api/authoring/worlds/{world_id}/nodes/{id}       -> 204 (delete node)
```
- `GraphSummary { world_id, region_count, entity_count, knowledge_count, prior_count, region_ids[] }`.

## CLI (Q3=A)
- `locus init-schema`(기존) / `build-wiki [--inputs path]` / `build-world --world <id> [--inputs path | --demo]` / `export --world <id> --out file.json`.

## Export (Q4=A)
- `export_world(world_id) -> dict`(regions/entities/knowledge/scopes/connections) → JSON 파일.

## Demo (Q5=A)
- `examples/demo_world/`(가상 세계 메모+맵) + `load_demo_world() -> WorldInputs`.

## 신규 컴포넌트
- `PipelineOrchestrator`, `GraphEditor`(upsert/delete + 재색인), `Exporter`(WorldLoader 직렬화), authoring router, app DI(factory 확장).
