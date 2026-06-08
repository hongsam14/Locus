# U8 Query & Serving — Business Logic Model

## WorldLoader (FD8-Q1=A)
- `load(world_id) -> (KnowledgeGraph, RegionTopology)`:
  1. nodes = graph_repo.find_nodes(world_id, label) for label in {Region, Entity, Knowledge, Rumor, WikiPrior}.
  2. edges = graph_repo.get_edges(world_id) (신규).
  3. 역매핑(graph_mapping reverse): nodes→domain models(prov_*/json 복원); CONTAINS→parent_id; CONNECTED_TO→ConnectionEdge; SCOPED_TO→ScopeLink; ABOUT/DERIVED_FROM→knowledge 필드.
  4. KnowledgeGraph(entities, knowledge, rumors, scopes) + RegionTopology(regions, connections) 반환.
- 캐시 없음(MVP); 소규모 가정.

## QueryEngine
- `knowledge_for_region(world_id, region_id, include_rumors=True) -> QueryResult`:
  - (kg, topo) = loader.load(world_id); region 없으면 LookupError(→404).
  - view = ConsensusEngine(kg, topo).resolve(region_id).
  - items = direct+inherited+global+propagated(+rumors if include_rumors).
  - unique_ids = [direct], shared_ids = [inherited+global+propagated+rumors].
- `diff_regions(world_id, a, b) -> RegionDiff`:
  - va, vb = resolve(a), resolve(b) (1회 load 공유).
  - set_a = known knowledge_ids of a(items), set_b = b.
  - shared = a∩b, only_a = a−b, only_b = b−a. (SC-2)

## Serving Router (`api/routers/query.py`, FastAPI)
- DI: QueryEngine(주입; app factory가 ProviderFactory/repos 연결).
- 엔드포인트: region knowledge / diff / health. 예외→HTTP(404 region 없음, 400 잘못된 파라미터, 500 기타).

## App factory (`api/main.py`)
- 설정으로 GraphRepository(Neo4j)/SearchRepository(OpenSearch) 생성·connect, QueryEngine 구성, serving router 등록. (authoring router는 U9.)
- 앱 시작 시 SchemaInitializer.initialize() (idempotent).

## 순수 분리
- 공유/고유·diff 집합 계산은 순수 함수(`split_shared_unique(view)`, `diff_sets(items_a, items_b)`) → 테스트. 로딩/엔진/HTTP는 mock.
