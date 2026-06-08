# U8 Query & Serving — Domain Entities & API Contract

결정: FD8 전부 A. U1/U5 모델 사용.

## Output 계약 (U1 모델)
- `QueryResult { world_id, region_id, items[KnowledgeView], shared_ids[], unique_ids[] }`.
- `RegionDiff { world_id, region_a, region_b, shared_ids[], only_a_ids[], only_b_ids[] }`.
- `KnowledgeView`: knowledge_id, statement, scope_type, is_rumor, distortion_degree?, confidence, source, region_id.

## 공유/고유 (FD8-Q3=A)
- 단일 지역: `unique_ids` = direct 항목, `shared_ids` = inherited+global+propagated+rumors 항목.
- items = direct+inherited+global+propagated+(include_rumors면 rumors).

## API (serving router, FD8-Q2=A)
```
GET /api/query/regions/{region_id}/knowledge?world_id=&include_rumors=true
    -> 200 QueryResult | 404 (region 없음)
GET /api/query/diff?world_id=&region_a=&region_b=
    -> 200 RegionDiff | 404
GET /health -> {status, neo4j, opensearch}   # 연결 점검(경량)
```
- 인증 없음(FD8-Q5=A). JSON 응답(Q10=A).

## 역매핑 규약 (WorldLoader, FD8-Q1=A)
- GraphRepository: `get_edges(world_id, types=None) -> list[Edge]` 추가(포트+Neo4j).
- `graph_mapping` 역함수: `node_to_region/entity/knowledge/rumor/wikiprior`(prov_*/json attributes 복원), 엣지→ConnectionEdge/ScopeLink/parent_id/about/derived 재구성.
- `WorldLoader.load(world_id) -> (KnowledgeGraph, RegionTopology)`.
